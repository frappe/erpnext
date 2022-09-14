# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe

# import erpnext
from frappe import _
from frappe.utils import cint, flt
from six import string_types

import erpnext
from erpnext.assets.doctype.asset.depreciation import (
	get_gl_entries_on_asset_disposal,
	get_value_after_depreciation_on_disposal_date,
)
from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account
from erpnext.assets.doctype.asset_value_adjustment.asset_value_adjustment import (
	get_current_asset_value,
)
from erpnext.controllers.stock_controller import StockController
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock import get_warehouse_account_map
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import (
	get_default_cost_center,
	get_default_expense_account,
	get_item_warehouse,
)
from erpnext.stock.stock_ledger import get_previous_sle
from erpnext.stock.utils import get_incoming_rate

force_fields = [
	"target_item_name",
	"target_asset_name",
	"item_name",
	"asset_name",
	"target_is_fixed_asset",
	"target_has_serial_no",
	"target_has_batch_no",
	"target_stock_uom",
	"stock_uom",
	"target_fixed_asset_account",
	"fixed_asset_account",
	"valuation_rate",
]


class AssetCapitalization(StockController):
	def validate(self):
		self.validate_posting_time()
		self.set_missing_values(for_validate=True)
		self.validate_target_item()
		self.validate_target_asset()
		self.validate_consumed_stock_item()
		self.validate_consumed_asset_item()
		self.validate_service_item()
		self.set_warehouse_details()
		self.set_asset_values()
		self.calculate_totals()
		self.set_title()

	def before_submit(self):
		self.validate_source_mandatory()

	def on_submit(self):
		self.update_stock_ledger()
		self.make_gl_entries()
		self.update_target_asset()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Repost Item Valuation")
		self.update_stock_ledger()
		self.make_gl_entries()
		self.update_target_asset()

	def set_title(self):
		self.title = self.target_asset_name or self.target_item_name or self.target_item_code

	def set_missing_values(self, for_validate=False):
		target_item_details = get_target_item_details(self.target_item_code, self.company)
		for k, v in target_item_details.items():
			if self.meta.has_field(k) and (not self.get(k) or k in force_fields):
				self.set(k, v)

		# Remove asset if item not a fixed asset
		if not self.target_is_fixed_asset:
			self.target_asset = None

		target_asset_details = get_target_asset_details(self.target_asset, self.company)
		for k, v in target_asset_details.items():
			if self.meta.has_field(k) and (not self.get(k) or k in force_fields):
				self.set(k, v)

		for d in self.stock_items:
			args = self.as_dict()
			args.update(d.as_dict())
			args.doctype = self.doctype
			args.name = self.name
			consumed_stock_item_details = get_consumed_stock_item_details(args)
			for k, v in consumed_stock_item_details.items():
				if d.meta.has_field(k) and (not d.get(k) or k in force_fields):
					d.set(k, v)

		for d in self.asset_items:
			args = self.as_dict()
			args.update(d.as_dict())
			args.doctype = self.doctype
			args.name = self.name
			args.finance_book = d.get("finance_book") or self.get("finance_book")
			consumed_asset_details = get_consumed_asset_details(args)
			for k, v in consumed_asset_details.items():
				if d.meta.has_field(k) and (not d.get(k) or k in force_fields):
					d.set(k, v)

		for d in self.service_items:
			args = self.as_dict()
			args.update(d.as_dict())
			args.doctype = self.doctype
			args.name = self.name
			service_item_details = get_service_item_details(args)
			for k, v in service_item_details.items():
				if d.meta.has_field(k) and (not d.get(k) or k in force_fields):
					d.set(k, v)

	def validate_target_item(self):
		target_item = frappe.get_cached_doc("Item", self.target_item_code)

		if not target_item.is_fixed_asset and not target_item.is_stock_item:
			frappe.throw(
				_("Target Item {0} is neither a Fixed Asset nor a Stock Item").format(target_item.name)
			)

		if self.entry_type == "Capitalization" and not target_item.is_fixed_asset:
			frappe.throw(_("Target Item {0} must be a Fixed Asset item").format(target_item.name))
		elif self.entry_type == "Decapitalization" and not target_item.is_stock_item:
			frappe.throw(_("Target Item {0} must be a Stock Item").format(target_item.name))

		if target_item.is_fixed_asset:
			self.target_qty = 1
		if flt(self.target_qty) <= 0:
			frappe.throw(_("Target Qty must be a positive number"))

		if not target_item.is_stock_item:
			self.target_warehouse = None
		if not target_item.is_fixed_asset:
			self.target_asset = None
			self.target_fixed_asset_account = None
		if not target_item.has_batch_no:
			self.target_batch_no = None
		if not target_item.has_serial_no:
			self.target_serial_no = ""

		if target_item.is_stock_item and not self.target_warehouse:
			frappe.throw(_("Target Warehouse is mandatory for Decapitalization"))

		self.validate_item(target_item)

	def validate_target_asset(self):
		if self.target_asset:
			target_asset = self.get_asset_for_validation(self.target_asset)

			if target_asset.item_code != self.target_item_code:
				frappe.throw(
					_("Asset {0} does not belong to Item {1}").format(self.target_asset, self.target_item_code)
				)

			self.validate_asset(target_asset)

	def validate_consumed_stock_item(self):
		for d in self.stock_items:
			if d.item_code:
				item = frappe.get_cached_doc("Item", d.item_code)

				if not item.is_stock_item:
					frappe.throw(_("Row #{0}: Item {1} is not a stock item").format(d.idx, d.item_code))

				if flt(d.stock_qty) <= 0:
					frappe.throw(_("Row #{0}: Qty must be a positive number").format(d.idx))

				self.validate_item(item)

	def validate_consumed_asset_item(self):
		for d in self.asset_items:
			if d.asset:
				if d.asset == self.target_asset:
					frappe.throw(
						_("Row #{0}: Consumed Asset {1} cannot be the same as the Target Asset").format(
							d.idx, d.asset
						)
					)

				asset = self.get_asset_for_validation(d.asset)
				self.validate_asset(asset)

	def validate_service_item(self):
		for d in self.service_items:
			if d.item_code:
				item = frappe.get_cached_doc("Item", d.item_code)

				if item.is_stock_item or item.is_fixed_asset:
					frappe.throw(_("Row #{0}: Item {1} is not a service item").format(d.idx, d.item_code))

				if flt(d.qty) <= 0:
					frappe.throw(_("Row #{0}: Qty must be a positive number").format(d.idx))

				if flt(d.rate) <= 0:
					frappe.throw(_("Row #{0}: Amount must be a positive number").format(d.idx))

				self.validate_item(item)

			if not d.cost_center:
				d.cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

	def validate_source_mandatory(self):
		if not self.target_is_fixed_asset and not self.get("asset_items"):
			frappe.throw(_("Consumed Asset Items is mandatory for Decapitalization"))

		if not self.get("stock_items") and not self.get("asset_items"):
			frappe.throw(_("Consumed Stock Items or Consumed Asset Items is mandatory for Capitalization"))

	def validate_item(self, item):
		from erpnext.stock.doctype.item.item import validate_end_of_life

		validate_end_of_life(item.name, item.end_of_life, item.disabled)

	def get_asset_for_validation(self, asset):
		return frappe.db.get_value(
			"Asset", asset, ["name", "item_code", "company", "status", "docstatus"], as_dict=1
		)

	def validate_asset(self, asset):
		if asset.status in ("Draft", "Scrapped", "Sold", "Capitalized", "Decapitalized"):
			frappe.throw(_("Asset {0} is {1}").format(asset.name, asset.status))

		if asset.docstatus == 0:
			frappe.throw(_("Asset {0} is Draft").format(asset.name))
		if asset.docstatus == 2:
			frappe.throw(_("Asset {0} is cancelled").format(asset.name))

		if asset.company != self.company:
			frappe.throw(_("Asset {0} does not belong to company {1}").format(asset.name, self.company))

	@frappe.whitelist()
	def set_warehouse_details(self):
		for d in self.get("stock_items"):
			if d.item_code and d.warehouse:
				args = self.get_args_for_incoming_rate(d)
				warehouse_details = get_warehouse_details(args)
				d.update(warehouse_details)

	@frappe.whitelist()
	def set_asset_values(self):
		for d in self.get("asset_items"):
			if d.asset:
				finance_book = d.get("finance_book") or self.get("finance_book")
				d.current_asset_value = flt(get_current_asset_value(d.asset, finance_book=finance_book))
				d.asset_value = get_value_after_depreciation_on_disposal_date(
					d.asset, self.posting_date, finance_book=finance_book
				)

	def get_args_for_incoming_rate(self, item):
		return frappe._dict(
			{
				"item_code": item.item_code,
				"warehouse": item.warehouse,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"qty": -1 * flt(item.stock_qty),
				"serial_no": item.serial_no,
				"batch_no": item.batch_no,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"company": self.company,
				"allow_zero_valuation": cint(item.get("allow_zero_valuation_rate")),
			}
		)

	def calculate_totals(self):
		self.stock_items_total = 0
		self.asset_items_total = 0
		self.service_items_total = 0

		for d in self.stock_items:
			d.amount = flt(flt(d.stock_qty) * flt(d.valuation_rate), d.precision("amount"))
			self.stock_items_total += d.amount

		for d in self.asset_items:
			d.asset_value = flt(flt(d.asset_value), d.precision("asset_value"))
			self.asset_items_total += d.asset_value

		for d in self.service_items:
			d.amount = flt(flt(d.qty) * flt(d.rate), d.precision("amount"))
			self.service_items_total += d.amount

		self.stock_items_total = flt(self.stock_items_total, self.precision("stock_items_total"))
		self.asset_items_total = flt(self.asset_items_total, self.precision("asset_items_total"))
		self.service_items_total = flt(self.service_items_total, self.precision("service_items_total"))

		self.total_value = self.stock_items_total + self.asset_items_total + self.service_items_total
		self.total_value = flt(self.total_value, self.precision("total_value"))

		self.target_qty = flt(self.target_qty, self.precision("target_qty"))
		self.target_incoming_rate = self.total_value / self.target_qty

	def update_stock_ledger(self):
		sl_entries = []

		for d in self.stock_items:
			sle = self.get_sl_entries(
				d,
				{
					"actual_qty": -flt(d.stock_qty),
				},
			)
			sl_entries.append(sle)

		if self.entry_type == "Decapitalization" and not self.target_is_fixed_asset:
			sle = self.get_sl_entries(
				self,
				{
					"item_code": self.target_item_code,
					"warehouse": self.target_warehouse,
					"batch_no": self.target_batch_no,
					"serial_no": self.target_serial_no,
					"actual_qty": flt(self.target_qty),
					"incoming_rate": flt(self.target_incoming_rate),
				},
			)
			sl_entries.append(sle)

		# reverse sl entries if cancel
		if self.docstatus == 2:
			sl_entries.reverse()

		if sl_entries:
			self.make_sl_entries(sl_entries)

	def make_gl_entries(self, gl_entries=None, from_repost=False):
		from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries

		if self.docstatus == 1:
			if not gl_entries:
				gl_entries = self.get_gl_entries()

			if gl_entries:
				make_gl_entries(gl_entries, from_repost=from_repost)
		elif self.docstatus == 2:
			make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

	def get_gl_entries(
		self, warehouse_account=None, default_expense_account=None, default_cost_center=None
	):
		# Stock GL Entries
		gl_entries = []

		self.warehouse_account = warehouse_account
		if not self.warehouse_account:
			self.warehouse_account = get_warehouse_account_map(self.company)

		precision = self.get_debit_field_precision()
		self.sle_map = self.get_stock_ledger_details()

		target_account = self.get_target_account()
		target_against = set()

		self.get_gl_entries_for_consumed_stock_items(
			gl_entries, target_account, target_against, precision
		)
		self.get_gl_entries_for_consumed_asset_items(
			gl_entries, target_account, target_against, precision
		)
		self.get_gl_entries_for_consumed_service_items(
			gl_entries, target_account, target_against, precision
		)

		self.get_gl_entries_for_target_item(gl_entries, target_against, precision)
		return gl_entries

	def get_target_account(self):
		if self.target_is_fixed_asset:
			return self.target_fixed_asset_account
		else:
			return self.warehouse_account[self.target_warehouse]["account"]

	def get_gl_entries_for_consumed_stock_items(
		self, gl_entries, target_account, target_against, precision
	):
		# Consumed Stock Items
		for item_row in self.stock_items:
			sle_list = self.sle_map.get(item_row.name)
			if sle_list:
				for sle in sle_list:
					stock_value_difference = flt(sle.stock_value_difference, precision)

					if erpnext.is_perpetual_inventory_enabled(self.company):
						account = self.warehouse_account[sle.warehouse]["account"]
					else:
						account = self.get_company_default("default_expense_account")

					target_against.add(account)
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": account,
								"against": target_account,
								"cost_center": item_row.cost_center,
								"project": item_row.get("project") or self.get("project"),
								"remarks": self.get("remarks") or "Accounting Entry for Stock",
								"credit": -1 * stock_value_difference,
							},
							self.warehouse_account[sle.warehouse]["account_currency"],
							item=item_row,
						)
					)

	def get_gl_entries_for_consumed_asset_items(
		self, gl_entries, target_account, target_against, precision
	):
		# Consumed Assets
		for item in self.asset_items:
			asset = self.get_asset(item)

			if asset.calculate_depreciation:
				self.depreciate_asset(asset)
				asset.reload()

			fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(
				asset, item.asset_value, item.get("finance_book") or self.get("finance_book")
			)

			asset.db_set("disposal_date", self.posting_date)

			self.set_consumed_asset_status(asset)

			for gle in fixed_asset_gl_entries:
				gle["against"] = target_account
				gl_entries.append(self.get_gl_dict(gle, item=item))
				target_against.add(gle["account"])

	def get_gl_entries_for_consumed_service_items(
		self, gl_entries, target_account, target_against, precision
	):
		# Service Expenses
		for item_row in self.service_items:
			expense_amount = flt(item_row.amount, precision)
			target_against.add(item_row.expense_account)

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": item_row.expense_account,
						"against": target_account,
						"cost_center": item_row.cost_center,
						"project": item_row.get("project") or self.get("project"),
						"remarks": self.get("remarks") or "Accounting Entry for Stock",
						"credit": expense_amount,
					},
					item=item_row,
				)
			)

	def get_gl_entries_for_target_item(self, gl_entries, target_against, precision):
		if self.target_is_fixed_asset:
			# Capitalization
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": self.target_fixed_asset_account,
						"against": ", ".join(target_against),
						"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
						"debit": flt(self.total_value, precision),
						"cost_center": self.get("cost_center"),
					},
					item=self,
				)
			)
		else:
			# Target Stock Item
			sle_list = self.sle_map.get(self.name)
			for sle in sle_list:
				stock_value_difference = flt(sle.stock_value_difference, precision)
				account = self.warehouse_account[sle.warehouse]["account"]

				gl_entries.append(
					self.get_gl_dict(
						{
							"account": account,
							"against": ", ".join(target_against),
							"cost_center": self.cost_center,
							"project": self.get("project"),
							"remarks": self.get("remarks") or "Accounting Entry for Stock",
							"debit": stock_value_difference,
						},
						self.warehouse_account[sle.warehouse]["account_currency"],
						item=self,
					)
				)

	def update_target_asset(self):
		total_target_asset_value = flt(self.total_value, self.precision("total_value"))
		if self.docstatus == 1 and self.entry_type == "Capitalization":
			asset_doc = frappe.get_doc("Asset", self.target_asset)
			asset_doc.purchase_date = self.posting_date
			asset_doc.gross_purchase_amount = total_target_asset_value
			asset_doc.purchase_receipt_amount = total_target_asset_value
			asset_doc.prepare_depreciation_data()
			asset_doc.flags.ignore_validate_update_after_submit = True
			asset_doc.save()
		elif self.docstatus == 2:
			for item in self.asset_items:
				asset = self.get_asset(item)
				asset.db_set("disposal_date", None)
				self.set_consumed_asset_status(asset)

				if asset.calculate_depreciation:
					self.reverse_depreciation_entry_made_after_disposal(asset)
					self.reset_depreciation_schedule(asset)

	def get_asset(self, item):
		asset = frappe.get_doc("Asset", item.asset)
		self.check_finance_books(item, asset)
		return asset

	def set_consumed_asset_status(self, asset):
		if self.docstatus == 1:
			asset.set_status("Capitalized" if self.target_is_fixed_asset else "Decapitalized")
		else:
			asset.set_status()


@frappe.whitelist()
def get_target_item_details(item_code=None, company=None):
	out = frappe._dict()

	# Get Item Details
	item = frappe._dict()
	if item_code:
		item = frappe.get_cached_doc("Item", item_code)

	# Set Item Details
	out.target_item_name = item.item_name
	out.target_stock_uom = item.stock_uom
	out.target_is_fixed_asset = cint(item.is_fixed_asset)
	out.target_has_batch_no = cint(item.has_batch_no)
	out.target_has_serial_no = cint(item.has_serial_no)

	if out.target_is_fixed_asset:
		out.target_qty = 1
		out.target_warehouse = None
	else:
		out.target_asset = None

	if not out.target_has_batch_no:
		out.target_batch_no = None
	if not out.target_has_serial_no:
		out.target_serial_no = ""

	# Cost Center
	item_defaults = get_item_defaults(item.name, company)
	item_group_defaults = get_item_group_defaults(item.name, company)
	brand_defaults = get_brand_defaults(item.name, company)
	out.cost_center = get_default_cost_center(
		frappe._dict({"item_code": item.name, "company": company}),
		item_defaults,
		item_group_defaults,
		brand_defaults,
	)

	return out


@frappe.whitelist()
def get_target_asset_details(asset=None, company=None):
	out = frappe._dict()

	# Get Asset Details
	asset_details = frappe._dict()
	if asset:
		asset_details = frappe.db.get_value("Asset", asset, ["asset_name", "item_code"], as_dict=1)
		if not asset_details:
			frappe.throw(_("Asset {0} does not exist").format(asset))

		# Re-set item code from Asset
		out.target_item_code = asset_details.item_code

	# Set Asset Details
	out.asset_name = asset_details.asset_name

	if asset_details.item_code:
		out.target_fixed_asset_account = get_asset_category_account(
			"fixed_asset_account", item=asset_details.item_code, company=company
		)
	else:
		out.target_fixed_asset_account = None

	return out


@frappe.whitelist()
def get_consumed_stock_item_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	item = frappe._dict()
	if args.item_code:
		item = frappe.get_cached_doc("Item", args.item_code)

	out.item_name = item.item_name
	out.batch_no = None
	out.serial_no = ""

	out.stock_qty = flt(args.stock_qty) or 1
	out.stock_uom = item.stock_uom

	out.warehouse = get_item_warehouse(item, args, overwrite_warehouse=True) if item else None

	# Cost Center
	item_defaults = get_item_defaults(item.name, args.company)
	item_group_defaults = get_item_group_defaults(item.name, args.company)
	brand_defaults = get_brand_defaults(item.name, args.company)
	out.cost_center = get_default_cost_center(
		args, item_defaults, item_group_defaults, brand_defaults
	)

	if args.item_code and out.warehouse:
		incoming_rate_args = frappe._dict(
			{
				"item_code": args.item_code,
				"warehouse": out.warehouse,
				"posting_date": args.posting_date,
				"posting_time": args.posting_time,
				"qty": -1 * flt(out.stock_qty),
				"voucher_type": args.doctype,
				"voucher_no": args.name,
				"company": args.company,
				"serial_no": args.serial_no,
				"batch_no": args.batch_no,
			}
		)
		out.update(get_warehouse_details(incoming_rate_args))
	else:
		out.valuation_rate = 0
		out.actual_qty = 0

	return out


@frappe.whitelist()
def get_warehouse_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)

	out = {}
	if args.warehouse and args.item_code:
		out = {
			"actual_qty": get_previous_sle(args).get("qty_after_transaction") or 0,
			"valuation_rate": get_incoming_rate(args, raise_error_if_no_rate=False),
		}
	return out


@frappe.whitelist()
def get_consumed_asset_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	asset_details = frappe._dict()
	if args.asset:
		asset_details = frappe.db.get_value(
			"Asset", args.asset, ["asset_name", "item_code", "item_name"], as_dict=1
		)
		if not asset_details:
			frappe.throw(_("Asset {0} does not exist").format(args.asset))

	out.item_code = asset_details.item_code
	out.asset_name = asset_details.asset_name
	out.item_name = asset_details.item_name

	if args.asset:
		out.current_asset_value = flt(
			get_current_asset_value(args.asset, finance_book=args.finance_book)
		)
		out.asset_value = get_value_after_depreciation_on_disposal_date(
			args.asset, args.posting_date, finance_book=args.finance_book
		)
	else:
		out.current_asset_value = 0
		out.asset_value = 0

	# Account
	if asset_details.item_code:
		out.fixed_asset_account = get_asset_category_account(
			"fixed_asset_account", item=asset_details.item_code, company=args.company
		)
	else:
		out.fixed_asset_account = None

	# Cost Center
	if asset_details.item_code:
		item = frappe.get_cached_doc("Item", asset_details.item_code)
		item_defaults = get_item_defaults(item.name, args.company)
		item_group_defaults = get_item_group_defaults(item.name, args.company)
		brand_defaults = get_brand_defaults(item.name, args.company)
		out.cost_center = get_default_cost_center(
			args, item_defaults, item_group_defaults, brand_defaults
		)

	return out


@frappe.whitelist()
def get_service_item_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	item = frappe._dict()
	if args.item_code:
		item = frappe.get_cached_doc("Item", args.item_code)

	out.item_name = item.item_name
	out.qty = flt(args.qty) or 1
	out.uom = item.purchase_uom or item.stock_uom

	item_defaults = get_item_defaults(item.name, args.company)
	item_group_defaults = get_item_group_defaults(item.name, args.company)
	brand_defaults = get_brand_defaults(item.name, args.company)

	out.expense_account = get_default_expense_account(
		args, item_defaults, item_group_defaults, brand_defaults
	)
	out.cost_center = get_default_cost_center(
		args, item_defaults, item_group_defaults, brand_defaults
	)

	return out
