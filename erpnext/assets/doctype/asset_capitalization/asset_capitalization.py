# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from erpnext.controllers.accounts_controller import AccountsController
from frappe.utils import cint, flt
from erpnext.stock.get_item_details import get_item_warehouse, get_default_expense_account, get_default_cost_center
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.stock.utils import get_incoming_rate
from erpnext.stock.stock_ledger import get_previous_sle
from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account
from erpnext.assets.doctype.asset_value_adjustment.asset_value_adjustment import get_current_asset_value
from six import string_types
import json

force_fields = ['target_item_name', 'target_asset_name', 'item_name', 'asset_name',
	'target_is_fixed_asset', 'target_has_serial_no', 'target_has_batch_no',
	'target_stock_uom', 'stock_uom', 'target_fixed_asset_account', 'fixed_asset_account']


class AssetCapitalization(AccountsController):
	def validate(self):
		self.validate_posting_time()
		self.set_missing_values(for_validate=True)
		self.set_entry_type()
		self.validate_target_item()
		self.validate_target_asset()
		self.validate_consumed_stock_item()
		self.validate_consumed_asset_item()
		self.validate_service_item()
		self.set_warehouse_details()
		self.set_asset_values()
		self.calculate_totals()
		self.set_title()

	def set_entry_type(self):
		self.entry_type = "Capitalization" if self.target_is_fixed_asset else "Decapitalization"

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
			consumed_stock_item_details = get_consumed_stock_item_details(args, get_valuation_rate=False)
			for k, v in consumed_stock_item_details.items():
				if d.meta.has_field(k) and (not d.get(k) or k in force_fields):
					d.set(k, v)

		for d in self.asset_items:
			args = self.as_dict()
			args.update(d.as_dict())
			args.doctype = self.doctype
			args.name = self.name
			consumed_asset_details = get_consumed_asset_details(args, get_asset_value=False)
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
			frappe.throw(_("Target Item {0} is neither a Fixed Asset nor a Stock Item")
				.format(target_item.name))

		if target_item.is_fixed_asset:
			self.target_qty = 1
		if flt(self.target_qty) <= 0:
			frappe.throw(_("Target Qty must be a positive number"))

		if not target_item.is_stock_item:
			self.target_warehouse = None
		if not target_item.is_fixed_asset:
			self.target_asset = None
		if not target_item.has_batch_no:
			self.target_batch_no = None
		if not target_item.has_serial_no:
			self.target_serial_no = ""

		self.validate_item(target_item)

	def validate_target_asset(self):
		if self.target_is_fixed_asset and not self.target_asset:
			frappe.throw(_("Target Asset is mandatory for Capitalization"))

		if self.target_asset:
			target_asset = self.get_asset_for_validation(self.target_asset)

			if target_asset.item_code != self.target_item_code:
				frappe.throw(_("Asset {0} does not belong to Item {1}").format(self.target_asset, self.target_item_code))

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
					frappe.throw(_("Row #{0}: Consumed Asset {1} cannot be the same as the Target Asset")
						.format(d.idx, d.asset))

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

				if flt(d.amount) <= 0:
					frappe.throw(_("Row #{0}: Amount must be a positive number").format(d.idx))

				self.validate_item(item)

			if not d.cost_center:
				d.cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

	def validate_item(self, item):
		from erpnext.stock.doctype.item.item import validate_end_of_life
		validate_end_of_life(item.name, item.end_of_life, item.disabled)

	def get_asset_for_validation(self, asset):
		return frappe.db.get_value("Asset", asset, ["name", "item_code", "company", "status", "docstatus"], as_dict=1)

	def validate_asset(self, asset):
		if asset.status in ("Draft", "Scrapped", "Sold"):
			frappe.throw(_("Asset {0} is {1}").format(asset.name, asset.status))

		if asset.docstatus == 0:
			frappe.throw(_("Asset {0} is Draft").format(asset.name))
		if asset.docstatus == 2:
			frappe.throw(_("Asset {0} is cancelled").format(asset.name))

		if asset.company != self.company:
			frappe.throw(_("Asset {0} does not belong to company {1}").format(self.target_asset, self.company))

	@frappe.whitelist()
	def set_warehouse_details(self):
		for d in self.stock_items:
			if d.item_code and d.warehouse:
				args = self.get_args_for_incoming_rate(d)
				warehouse_details = get_warehouse_details(args)
				d.update(warehouse_details)

	@frappe.whitelist()
	def set_asset_values(self):
		for d in self.asset_items:
			if d.asset:
				d.asset_value = flt(get_current_asset_value(d.asset, self.finance_book))

	def get_args_for_incoming_rate(self, item):
		return frappe._dict({
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
			"allow_zero_valuation": cint(item.get('allow_zero_valuation_rate')),
		})

	def calculate_totals(self):
		self.stock_items_total = 0
		self.asset_items_total = 0
		self.service_items_total = 0

		for d in self.stock_items:
			d.amount = flt(flt(d.stock_qty) * flt(d.valuation_rate), d.precision('amount'))
			self.stock_items_total += d.amount

		for d in self.asset_items:
			d.asset_value = flt(flt(d.asset_value), d.precision('asset_value'))
			self.asset_items_total += d.asset_value

		for d in self.service_items:
			d.amount = flt(flt(d.qty) * flt(d.rate), d.precision('amount'))
			self.service_items_total += d.amount

		self.stock_items_total = flt(self.stock_items_total, self.precision('stock_items_total'))
		self.asset_items_total = flt(self.asset_items_total, self.precision('asset_items_total'))
		self.service_items_total = flt(self.service_items_total, self.precision('service_items_total'))

		self.total_value = self.stock_items_total + self.asset_items_total + self.service_items_total
		self.total_value = flt(self.total_value, self.precision('total_value'))

		self.target_qty = flt(self.target_qty, self.precision('target_qty'))
		self.target_incoming_rate = self.total_value / self.target_qty


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
	out.cost_center = get_default_cost_center(frappe._dict({'item_code': item.name, 'company': company}),
		item_defaults, item_group_defaults, brand_defaults)

	# Set Entry Type
	if not item_code:
		out.entry_type = ""
	elif out.target_is_fixed_asset:
		out.entry_type = "Capitalization"
	else:
		out.entry_type = "Decapitalization"

	return out


@frappe.whitelist()
def get_target_asset_details(asset=None, company=None):
	out = frappe._dict()

	# Get Asset Details
	asset_details = frappe._dict()
	if asset:
		asset_details = frappe.db.get_value("Asset", asset, ['asset_name', 'item_code'], as_dict=1)
		if not asset_details:
			frappe.throw(_("Asset {0} does not exist").format(asset))

		# Re-set item code from Asset
		out.target_item_code = asset_details.item_code

	# Set Asset Details
	out.asset_name = asset_details.asset_name

	if asset_details.item_code:
		out.target_fixed_asset_account = get_asset_category_account('fixed_asset_account', item=asset_details.item_code,
			company=company)
	else:
		out.target_fixed_asset_account = None

	return out


@frappe.whitelist()
def get_consumed_stock_item_details(args, get_valuation_rate=True):
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
	out.cost_center = get_default_cost_center(args, item_defaults, item_group_defaults, brand_defaults)

	if get_valuation_rate:
		if args.item_code and out.warehouse:
			incoming_rate_args = frappe._dict({
				'item_code': args.item_code,
				'warehouse': out.warehouse,
				'posting_date': args.posting_date,
				'posting_time': args.posting_time,
				'qty': -1 * flt(out.stock_qty),
				"voucher_type": args.doctype,
				"voucher_no": args.name,
				"company": args.company,
			})
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
			"valuation_rate": get_incoming_rate(args, raise_error_if_no_rate=False)
		}
	return out


@frappe.whitelist()
def get_consumed_asset_details(args, get_asset_value=True):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	asset_details = frappe._dict()
	if args.asset:
		asset_details = frappe.db.get_value("Asset", args.asset, ['asset_name', 'item_code', 'item_name'], as_dict=1)
		if not asset_details:
			frappe.throw(_("Asset {0} does not exist").format(args.asset))

	out.item_code = asset_details.item_code
	out.asset_name = asset_details.asset_name
	out.item_name = asset_details.item_name

	if get_asset_value:
		if args.asset:
			out.asset_value = flt(get_current_asset_value(args.asset, finance_book=args.finance_book))
		else:
			out.asset_value = 0

	# Account
	if asset_details.item_code:
		out.fixed_asset_account = get_asset_category_account('fixed_asset_account', item=asset_details.item_code,
			company=args.company)
	else:
		out.fixed_asset_account = None

	# Cost Center
	if asset_details.item_code:
		item = frappe.get_cached_doc("Item", asset_details.item_code)
		item_defaults = get_item_defaults(item.name, args.company)
		item_group_defaults = get_item_group_defaults(item.name, args.company)
		brand_defaults = get_brand_defaults(item.name, args.company)
		out.cost_center = get_default_cost_center(args, item_defaults, item_group_defaults, brand_defaults)

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

	out.expense_account = get_default_expense_account(args, item_defaults, item_group_defaults, brand_defaults)
	out.cost_center = get_default_cost_center(args, item_defaults, item_group_defaults, brand_defaults)

	return out
