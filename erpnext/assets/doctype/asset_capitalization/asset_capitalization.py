# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe

# import erpnext
from frappe import _
from frappe.utils import cint, flt, get_link_to_form

import erpnext
from erpnext.assets.doctype.asset.asset import get_asset_value_after_depreciation
from erpnext.assets.doctype.asset.depreciation import (
	depreciate_asset,
<<<<<<< HEAD
	get_disposal_account_and_cost_center,
	get_gl_entries_on_asset_disposal,
	get_value_after_depreciation_on_disposal_date,
	reset_depreciation_schedule,
	reverse_depreciation_entry_made_on_disposal,
=======
	get_gl_entries_on_asset_disposal,
	get_value_after_depreciation_on_disposal_date,
	reset_depreciation_schedule,
	reverse_depreciation_entry_made_after_disposal,
>>>>>>> 7c4cf3e834 (Favicon.svg)
)
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account
from erpnext.controllers.stock_controller import StockController
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
<<<<<<< HEAD
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import (
	ItemDetailsCtx,
	get_default_cost_center,
	get_default_expense_account,
	get_item_warehouse_,
=======
from erpnext.stock import get_warehouse_account_map
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import (
	get_default_cost_center,
	get_default_expense_account,
	get_item_warehouse,
>>>>>>> 7c4cf3e834 (Favicon.svg)
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
<<<<<<< HEAD
=======
	"target_stock_uom",
>>>>>>> 7c4cf3e834 (Favicon.svg)
	"stock_uom",
	"fixed_asset_account",
	"valuation_rate",
]


class AssetCapitalization(StockController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.assets.doctype.asset_capitalization_asset_item.asset_capitalization_asset_item import (
			AssetCapitalizationAssetItem,
		)
		from erpnext.assets.doctype.asset_capitalization_service_item.asset_capitalization_service_item import (
			AssetCapitalizationServiceItem,
		)
		from erpnext.assets.doctype.asset_capitalization_stock_item.asset_capitalization_stock_item import (
			AssetCapitalizationStockItem,
		)

		amended_from: DF.Link | None
		asset_items: DF.Table[AssetCapitalizationAssetItem]
		asset_items_total: DF.Currency
<<<<<<< HEAD
		company: DF.Link
		cost_center: DF.Link | None
=======
		capitalization_method: DF.Literal["", "Create a new composite asset", "Choose a WIP composite asset"]
		company: DF.Link
		cost_center: DF.Link | None
		entry_type: DF.Literal["Capitalization", "Decapitalization"]
>>>>>>> 7c4cf3e834 (Favicon.svg)
		finance_book: DF.Link | None
		naming_series: DF.Literal["ACC-ASC-.YYYY.-"]
		posting_date: DF.Date
		posting_time: DF.Time
		service_items: DF.Table[AssetCapitalizationServiceItem]
		service_items_total: DF.Currency
		set_posting_time: DF.Check
		stock_items: DF.Table[AssetCapitalizationStockItem]
		stock_items_total: DF.Currency
		target_asset: DF.Link | None
<<<<<<< HEAD
=======
		target_asset_location: DF.Link | None
>>>>>>> 7c4cf3e834 (Favicon.svg)
		target_asset_name: DF.Data | None
		target_batch_no: DF.Link | None
		target_fixed_asset_account: DF.Link | None
		target_has_batch_no: DF.Check
		target_has_serial_no: DF.Check
		target_incoming_rate: DF.Currency
		target_is_fixed_asset: DF.Check
		target_item_code: DF.Link | None
<<<<<<< HEAD
		target_qty: DF.Float
		target_serial_no: DF.SmallText | None
=======
		target_item_name: DF.Data | None
		target_qty: DF.Float
		target_serial_no: DF.SmallText | None
		target_stock_uom: DF.Link | None
		target_warehouse: DF.Link | None
>>>>>>> 7c4cf3e834 (Favicon.svg)
		title: DF.Data | None
		total_value: DF.Currency
	# end: auto-generated types

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

	def on_update(self):
		if self.stock_items:
			self.set_serial_and_batch_bundle(table_name="stock_items")

	def before_submit(self):
		self.validate_source_mandatory()
<<<<<<< HEAD
		# self.create_target_asset()
=======
		self.create_target_asset()
>>>>>>> 7c4cf3e834 (Favicon.svg)

	def on_submit(self):
		self.make_bundle_using_old_serial_batch_fields()
		self.update_stock_ledger()
		self.make_gl_entries()
<<<<<<< HEAD
		self.repost_future_sle_and_gle()
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
		self.update_target_asset()

	def on_cancel(self):
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Stock Ledger Entry",
			"Repost Item Valuation",
			"Serial and Batch Bundle",
			"Asset",
			"Asset Movement",
		)
		self.update_stock_ledger()
		self.make_gl_entries()
<<<<<<< HEAD
		self.repost_future_sle_and_gle()
		self.restore_consumed_asset_items()
		self.update_target_asset()

	def set_title(self):
		self.title = self.target_asset_name or self.target_item_code
=======
		self.restore_consumed_asset_items()

	def set_title(self):
		self.title = self.target_asset_name or self.target_item_name or self.target_item_code
>>>>>>> 7c4cf3e834 (Favicon.svg)

	def set_missing_values(self, for_validate=False):
		target_item_details = get_target_item_details(self.target_item_code, self.company)
		for k, v in target_item_details.items():
			if self.meta.has_field(k) and (not self.get(k) or k in force_fields):
				self.set(k, v)

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

<<<<<<< HEAD
		if not target_item.is_fixed_asset:
			frappe.throw(_("Target Item {0} must be a Fixed Asset item").format(target_item.name))
=======
		if not target_item.is_fixed_asset and not target_item.is_stock_item:
			frappe.throw(
				_("Target Item {0} is neither a Fixed Asset nor a Stock Item").format(target_item.name)
			)

		if self.entry_type == "Capitalization" and not target_item.is_fixed_asset:
			frappe.throw(_("Target Item {0} must be a Fixed Asset item").format(target_item.name))
		elif self.entry_type == "Decapitalization" and not target_item.is_stock_item:
			frappe.throw(_("Target Item {0} must be a Stock Item").format(target_item.name))
>>>>>>> 7c4cf3e834 (Favicon.svg)

		if target_item.is_fixed_asset:
			self.target_qty = 1
		if flt(self.target_qty) <= 0:
			frappe.throw(_("Target Qty must be a positive number"))
<<<<<<< HEAD
=======

		if not target_item.is_stock_item:
			self.target_warehouse = None
>>>>>>> 7c4cf3e834 (Favicon.svg)
		if not target_item.has_batch_no:
			self.target_batch_no = None
		if not target_item.has_serial_no:
			self.target_serial_no = ""

<<<<<<< HEAD
=======
		if target_item.is_stock_item and not self.target_warehouse:
			frappe.throw(_("Target Warehouse is mandatory for Decapitalization"))

>>>>>>> 7c4cf3e834 (Favicon.svg)
		self.validate_item(target_item)

	def validate_target_asset(self):
		if self.target_asset:
			target_asset = self.get_asset_for_validation(self.target_asset)

			if not target_asset.is_composite_asset:
				frappe.throw(_("Target Asset {0} needs to be composite asset").format(target_asset.name))

			if target_asset.item_code != self.target_item_code:
				frappe.throw(
					_("Asset {0} does not belong to Item {1}").format(
						self.target_asset, self.target_item_code
					)
				)

<<<<<<< HEAD
			if target_asset.status in ("Scrapped", "Sold", "Capitalized"):
=======
			if target_asset.status in ("Scrapped", "Sold", "Capitalized", "Decapitalized"):
>>>>>>> 7c4cf3e834 (Favicon.svg)
				frappe.throw(
					_("Target Asset {0} cannot be {1}").format(target_asset.name, target_asset.status)
				)

			if target_asset.docstatus == 1:
				frappe.throw(_("Target Asset {0} cannot be submitted").format(target_asset.name))
			elif target_asset.docstatus == 2:
				frappe.throw(_("Target Asset {0} cannot be cancelled").format(target_asset.name))

			if target_asset.company != self.company:
				frappe.throw(
					_("Target Asset {0} does not belong to company {1}").format(
						target_asset.name, self.company
					)
				)

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

<<<<<<< HEAD
				if asset.status in ("Draft", "Scrapped", "Sold", "Capitalized"):
=======
				if asset.status in ("Draft", "Scrapped", "Sold", "Capitalized", "Decapitalized"):
>>>>>>> 7c4cf3e834 (Favicon.svg)
					frappe.throw(
						_("Row #{0}: Consumed Asset {1} cannot be {2}").format(
							d.idx, asset.name, asset.status
						)
					)

				if asset.docstatus == 0:
					frappe.throw(_("Row #{0}: Consumed Asset {1} cannot be Draft").format(d.idx, asset.name))
				elif asset.docstatus == 2:
					frappe.throw(
						_("Row #{0}: Consumed Asset {1} cannot be cancelled").format(d.idx, asset.name)
					)

				if asset.company != self.company:
					frappe.throw(
						_("Row #{0}: Consumed Asset {1} does not belong to company {2}").format(
							d.idx, asset.name, self.company
						)
					)

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
<<<<<<< HEAD
		if not (self.get("stock_items") or self.get("asset_items") or self.get("service_items")):
=======
		if not self.target_is_fixed_asset and not self.get("asset_items"):
			frappe.throw(_("Consumed Asset Items is mandatory for Decapitalization"))

		if self.capitalization_method == "Create a new composite asset" and not (
			self.get("stock_items") or self.get("asset_items")
		):
			frappe.throw(
				_(
					"Consumed Stock Items or Consumed Asset Items are mandatory for creating new composite asset"
				)
			)

		elif not (self.get("stock_items") or self.get("asset_items") or self.get("service_items")):
>>>>>>> 7c4cf3e834 (Favicon.svg)
			frappe.throw(
				_(
					"Consumed Stock Items, Consumed Asset Items or Consumed Service Items is mandatory for Capitalization"
				)
			)

	def validate_item(self, item):
		from erpnext.stock.doctype.item.item import validate_end_of_life

		validate_end_of_life(item.name, item.end_of_life, item.disabled)

	def get_asset_for_validation(self, asset):
		return frappe.db.get_value(
			"Asset",
			asset,
			["name", "item_code", "company", "status", "docstatus", "is_composite_asset"],
			as_dict=1,
		)

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
				d.current_asset_value = flt(
					get_asset_value_after_depreciation(d.asset, finance_book=finance_book)
				)
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
				{"actual_qty": -flt(d.stock_qty), "serial_and_batch_bundle": d.serial_and_batch_bundle},
			)
			sl_entries.append(sle)

<<<<<<< HEAD
=======
		if self.entry_type == "Decapitalization" and not self.target_is_fixed_asset:
			sle = self.get_sl_entries(
				self,
				{
					"item_code": self.target_item_code,
					"warehouse": self.target_warehouse,
					"actual_qty": flt(self.target_qty),
					"incoming_rate": flt(self.target_incoming_rate),
				},
			)
			sl_entries.append(sle)

>>>>>>> 7c4cf3e834 (Favicon.svg)
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
				make_gl_entries(gl_entries, merge_entries=False, from_repost=from_repost)
		elif self.docstatus == 2:
			make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

<<<<<<< HEAD
	def get_gl_entries(
		self, inventory_account_map=None, default_expense_account=None, default_cost_center=None
	):
		# Stock GL Entries
		gl_entries = []

		self.inventory_account_map = inventory_account_map
		if not self.inventory_account_map:
			self.inventory_account_map = self.get_inventory_account_map()
=======
	def get_gl_entries(self, warehouse_account=None, default_expense_account=None, default_cost_center=None):
		# Stock GL Entries
		gl_entries = []

		self.warehouse_account = warehouse_account
		if not self.warehouse_account:
			self.warehouse_account = get_warehouse_account_map(self.company)
>>>>>>> 7c4cf3e834 (Favicon.svg)

		precision = self.get_debit_field_precision()
		self.sle_map = self.get_stock_ledger_details()

		target_account = self.get_target_account()
		target_against = set()

		self.get_gl_entries_for_consumed_stock_items(gl_entries, target_account, target_against, precision)
		self.get_gl_entries_for_consumed_asset_items(gl_entries, target_account, target_against, precision)
		self.get_gl_entries_for_consumed_service_items(gl_entries, target_account, target_against, precision)

<<<<<<< HEAD
		composite_component_value = self.get_composite_component_value()

		self.get_gl_entries_for_target_item(
			gl_entries, target_account, target_against, precision, composite_component_value
		)
=======
		self.get_gl_entries_for_target_item(gl_entries, target_account, target_against, precision)
>>>>>>> 7c4cf3e834 (Favicon.svg)

		return gl_entries

	def get_target_account(self):
<<<<<<< HEAD
		from erpnext.assets.doctype.asset.asset import is_cwip_accounting_enabled

		asset_category = frappe.get_cached_value("Asset", self.target_asset, "asset_category")
		if is_cwip_accounting_enabled(asset_category):
			target_account = get_asset_category_account(
				"capital_work_in_progress_account",
				asset_category=asset_category,
				company=self.company,
			)
			return target_account if target_account else self.target_fixed_asset_account
		else:
			return self.target_fixed_asset_account
=======
		if self.target_is_fixed_asset:
			from erpnext.assets.doctype.asset.asset import is_cwip_accounting_enabled

			asset_category = frappe.get_cached_value("Asset", self.target_asset, "asset_category")
			if is_cwip_accounting_enabled(asset_category):
				target_account = get_asset_category_account(
					"capital_work_in_progress_account",
					asset_category=asset_category,
					company=self.company,
				)
				return target_account if target_account else self.target_fixed_asset_account
			else:
				return self.target_fixed_asset_account
		else:
			return self.warehouse_account[self.target_warehouse]["account"]
>>>>>>> 7c4cf3e834 (Favicon.svg)

	def get_gl_entries_for_consumed_stock_items(self, gl_entries, target_account, target_against, precision):
		# Consumed Stock Items
		for item_row in self.stock_items:
			sle_list = self.sle_map.get(item_row.name)
			if sle_list:
<<<<<<< HEAD
				_inv_dict = self.get_inventory_account_dict(item_row, self.inventory_account_map)
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
				for sle in sle_list:
					stock_value_difference = flt(sle.stock_value_difference, precision)

					if erpnext.is_perpetual_inventory_enabled(self.company):
<<<<<<< HEAD
						account = _inv_dict["account"]
=======
						account = self.warehouse_account[sle.warehouse]["account"]
>>>>>>> 7c4cf3e834 (Favicon.svg)
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
<<<<<<< HEAD
							_inv_dict["account_currency"],
=======
							self.warehouse_account[sle.warehouse]["account_currency"],
>>>>>>> 7c4cf3e834 (Favicon.svg)
							item=item_row,
						)
					)

	def get_gl_entries_for_consumed_asset_items(self, gl_entries, target_account, target_against, precision):
		# Consumed Assets
		for item in self.asset_items:
			asset = frappe.get_doc("Asset", item.asset)

<<<<<<< HEAD
			if not asset.is_composite_component:
				if asset.calculate_depreciation:
					notes = _(
						"This schedule was created when Asset {0} was consumed through Asset Capitalization {1}."
					).format(
						get_link_to_form(asset.doctype, asset.name),
						get_link_to_form(self.doctype, self.get("name")),
					)
					depreciate_asset(asset, self.posting_date, notes)
					asset.reload()

				fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(
					asset,
					item.asset_value,
					item.get("finance_book") or self.get("finance_book"),
					self.get("doctype"),
					self.get("name"),
					self.get("posting_date"),
				)

				for gle in fixed_asset_gl_entries:
					gle["against"] = target_account
					gl_entries.append(self.get_gl_dict(gle, item=item))
					target_against.add(gle["account"])

			asset.db_set("disposal_date", self.posting_date)
			self.set_consumed_asset_status(asset)

=======
			if asset.calculate_depreciation:
				notes = _(
					"This schedule was created when Asset {0} was consumed through Asset Capitalization {1}."
				).format(
					get_link_to_form(asset.doctype, asset.name),
					get_link_to_form(self.doctype, self.get("name")),
				)
				depreciate_asset(asset, self.posting_date, notes)
				asset.reload()

			fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(
				asset,
				item.asset_value,
				item.get("finance_book") or self.get("finance_book"),
				self.get("doctype"),
				self.get("name"),
				self.get("posting_date"),
			)

			asset.db_set("disposal_date", self.posting_date)

			self.set_consumed_asset_status(asset)

			for gle in fixed_asset_gl_entries:
				gle["against"] = target_account
				gl_entries.append(self.get_gl_dict(gle, item=item))
				target_against.add(gle["account"])

>>>>>>> 7c4cf3e834 (Favicon.svg)
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

<<<<<<< HEAD
	def get_composite_component_value(self):
		composite_component_value = 0
		for item in self.asset_items:
			asset = frappe.db.get_value("Asset", item.asset, ["is_composite_component"], as_dict=True)
			if asset and asset.is_composite_component:
				composite_component_value += flt(item.asset_value, item.precision("asset_value"))
		return composite_component_value

	def get_gl_entries_for_target_item(
		self, gl_entries, target_account, target_against, precision, composite_component_value
	):
		if self.target_is_fixed_asset:
			total_value = flt(self.total_value - composite_component_value, precision)
			if total_value:
				# Capitalization
				gl_entries.append(
					self.get_gl_dict(
						{
							"account": target_account,
							"against": ", ".join(target_against),
							"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
							"debit": total_value,
							"cost_center": self.get("cost_center"),
						},
=======
	def get_gl_entries_for_target_item(self, gl_entries, target_account, target_against, precision):
		if self.target_is_fixed_asset:
			# Capitalization
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": target_account,
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
>>>>>>> 7c4cf3e834 (Favicon.svg)
						item=self,
					)
				)

<<<<<<< HEAD
	def update_target_asset(self):
		total_target_asset_value = flt(self.total_value, self.precision("total_value"))
		asset_doc = frappe.get_doc("Asset", self.target_asset)

		if self.docstatus == 2:
			net_purchase_amount = asset_doc.net_purchase_amount - total_target_asset_value
			purchase_amount = asset_doc.purchase_amount - total_target_asset_value
			asset_doc.db_set("total_asset_cost", asset_doc.total_asset_cost - total_target_asset_value)
		else:
			net_purchase_amount = asset_doc.net_purchase_amount + total_target_asset_value
			purchase_amount = asset_doc.purchase_amount + total_target_asset_value

		asset_doc.db_set("net_purchase_amount", net_purchase_amount)
		asset_doc.db_set("purchase_amount", purchase_amount)
=======
	def create_target_asset(self):
		if (
			self.entry_type != "Capitalization"
			or self.capitalization_method != "Create a new composite asset"
		):
			return

		total_target_asset_value = flt(self.total_value, self.precision("total_value"))

		asset_doc = frappe.new_doc("Asset")
		asset_doc.company = self.company
		asset_doc.item_code = self.target_item_code
		asset_doc.is_composite_asset = 1
		asset_doc.location = self.target_asset_location
		asset_doc.available_for_use_date = self.posting_date
		asset_doc.purchase_date = self.posting_date
		asset_doc.gross_purchase_amount = total_target_asset_value
		asset_doc.purchase_amount = total_target_asset_value
		asset_doc.flags.ignore_validate = True
		asset_doc.flags.asset_created_via_asset_capitalization = True
		asset_doc.insert()

		self.target_asset = asset_doc.name

		self.target_fixed_asset_account = get_asset_category_account(
			"fixed_asset_account", item=self.target_item_code, company=asset_doc.company
		)

		add_asset_activity(
			asset_doc.name,
			_("Asset created after Asset Capitalization {0} was submitted").format(
				get_link_to_form("Asset Capitalization", self.name)
			),
		)

		frappe.msgprint(
			_("Asset {0} has been created. Please set the depreciation details if any and submit it.").format(
				get_link_to_form("Asset", asset_doc.name)
			)
		)

	def update_target_asset(self):
		if (
			self.entry_type != "Capitalization"
			or self.capitalization_method != "Choose a WIP composite asset"
		):
			return

		total_target_asset_value = flt(self.total_value, self.precision("total_value"))

		asset_doc = frappe.get_doc("Asset", self.target_asset)
		asset_doc.gross_purchase_amount = total_target_asset_value
		asset_doc.purchase_amount = total_target_asset_value
		asset_doc.flags.ignore_validate = True
		asset_doc.save()
>>>>>>> 7c4cf3e834 (Favicon.svg)

		frappe.msgprint(
			_("Asset {0} has been updated. Please set the depreciation details if any and submit it.").format(
				get_link_to_form("Asset", asset_doc.name)
			)
		)

	def restore_consumed_asset_items(self):
		for item in self.asset_items:
			asset = frappe.get_doc("Asset", item.asset)
<<<<<<< HEAD
			self.set_consumed_asset_status(asset)

			if asset.calculate_depreciation:
				reverse_depreciation_entry_made_on_disposal(asset)
=======
			asset.db_set("disposal_date", None)
			self.set_consumed_asset_status(asset)

			if asset.calculate_depreciation:
				reverse_depreciation_entry_made_after_disposal(asset, self.posting_date)
>>>>>>> 7c4cf3e834 (Favicon.svg)
				notes = _(
					"This schedule was created when Asset {0} was restored on Asset Capitalization {1}'s cancellation."
				).format(
					get_link_to_form(asset.doctype, asset.name), get_link_to_form(self.doctype, self.name)
				)
<<<<<<< HEAD
				reset_depreciation_schedule(asset, notes)
			asset.db_set("disposal_date", None)
=======
				reset_depreciation_schedule(asset, self.posting_date, notes)
>>>>>>> 7c4cf3e834 (Favicon.svg)

	def set_consumed_asset_status(self, asset):
		if self.docstatus == 1:
			if self.target_is_fixed_asset:
				asset.set_status("Capitalized")
				add_asset_activity(
					asset.name,
					_("Asset capitalized after Asset Capitalization {0} was submitted").format(
						get_link_to_form("Asset Capitalization", self.name)
					),
				)
<<<<<<< HEAD
=======
			else:
				asset.set_status("Decapitalized")
				add_asset_activity(
					asset.name,
					_("Asset decapitalized after Asset Capitalization {0} was submitted").format(
						get_link_to_form("Asset Capitalization", self.name)
					),
				)
>>>>>>> 7c4cf3e834 (Favicon.svg)
		else:
			asset.set_status()
			add_asset_activity(
				asset.name,
				_("Asset restored after Asset Capitalization {0} was cancelled").format(
					get_link_to_form("Asset Capitalization", self.name)
				),
			)


@frappe.whitelist()
def get_target_item_details(item_code=None, company=None):
	out = frappe._dict()

	# Get Item Details
	item = frappe._dict()
	if item_code:
		item = frappe.get_cached_doc("Item", item_code)

	# Set Item Details
	out.target_item_name = item.item_name
<<<<<<< HEAD
=======
	out.target_stock_uom = item.stock_uom
>>>>>>> 7c4cf3e834 (Favicon.svg)
	out.target_is_fixed_asset = cint(item.is_fixed_asset)
	out.target_has_batch_no = cint(item.has_batch_no)
	out.target_has_serial_no = cint(item.has_serial_no)

	if out.target_is_fixed_asset:
		out.target_qty = 1
<<<<<<< HEAD
=======
		out.target_warehouse = None
	else:
		out.target_asset = None
>>>>>>> 7c4cf3e834 (Favicon.svg)

	if not out.target_has_batch_no:
		out.target_batch_no = None
	if not out.target_has_serial_no:
		out.target_serial_no = ""

	# Cost Center
	item_defaults = get_item_defaults(item.name, company)
	item_group_defaults = get_item_group_defaults(item.name, company)
	brand_defaults = get_brand_defaults(item.name, company)
	out.cost_center = get_default_cost_center(
<<<<<<< HEAD
		ItemDetailsCtx({"item_code": item.name, "company": company}),
=======
		frappe._dict({"item_code": item.name, "company": company}),
>>>>>>> 7c4cf3e834 (Favicon.svg)
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
<<<<<<< HEAD
@erpnext.normalize_ctx_input(ItemDetailsCtx)
def get_consumed_stock_item_details(ctx: ItemDetailsCtx):
	out = frappe._dict()

	item = frappe._dict()
	if ctx.item_code:
		item = frappe.get_cached_doc("Item", ctx.item_code)
=======
def get_consumed_stock_item_details(args):
	if isinstance(args, str):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	item = frappe._dict()
	if args.item_code:
		item = frappe.get_cached_doc("Item", args.item_code)
>>>>>>> 7c4cf3e834 (Favicon.svg)

	out.item_name = item.item_name
	out.batch_no = None
	out.serial_no = ""

<<<<<<< HEAD
	out.stock_qty = flt(ctx.stock_qty) or 1
	out.stock_uom = item.stock_uom

	out.warehouse = get_item_warehouse_(ctx, item, overwrite_warehouse=True) if item else None

	# Cost Center
	item_defaults = get_item_defaults(item.name, ctx.company)
	item_group_defaults = get_item_group_defaults(item.name, ctx.company)
	brand_defaults = get_brand_defaults(item.name, ctx.company)
	out.cost_center = get_default_cost_center(ctx, item_defaults, item_group_defaults, brand_defaults)

	if ctx.item_code and out.warehouse:
		incoming_rate_args = frappe._dict(
			{
				"item_code": ctx.item_code,
				"warehouse": out.warehouse,
				"posting_date": ctx.posting_date,
				"posting_time": ctx.posting_time,
				"qty": -1 * flt(out.stock_qty),
				"voucher_type": ctx.doctype,
				"voucher_no": ctx.name,
				"company": ctx.company,
				"serial_no": ctx.serial_no,
				"batch_no": ctx.batch_no,
=======
	out.stock_qty = flt(args.stock_qty) or 1
	out.stock_uom = item.stock_uom

	out.warehouse = get_item_warehouse(item, args, overwrite_warehouse=True) if item else None

	# Cost Center
	item_defaults = get_item_defaults(item.name, args.company)
	item_group_defaults = get_item_group_defaults(item.name, args.company)
	brand_defaults = get_brand_defaults(item.name, args.company)
	out.cost_center = get_default_cost_center(args, item_defaults, item_group_defaults, brand_defaults)

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
>>>>>>> 7c4cf3e834 (Favicon.svg)
			}
		)
		out.update(get_warehouse_details(incoming_rate_args))
	else:
		out.valuation_rate = 0
		out.actual_qty = 0

	return out


@frappe.whitelist()
def get_warehouse_details(args):
	if isinstance(args, str):
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
<<<<<<< HEAD
@erpnext.normalize_ctx_input(ItemDetailsCtx)
def get_consumed_asset_details(ctx):
	out = frappe._dict()

	asset_details = frappe._dict()
	if ctx.asset:
		asset_details = frappe.db.get_value(
			"Asset", ctx.asset, ["asset_name", "item_code", "item_name"], as_dict=1
		)
		if not asset_details:
			frappe.throw(_("Asset {0} does not exist").format(ctx.asset))
=======
def get_consumed_asset_details(args):
	if isinstance(args, str):
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
>>>>>>> 7c4cf3e834 (Favicon.svg)

	out.item_code = asset_details.item_code
	out.asset_name = asset_details.asset_name
	out.item_name = asset_details.item_name

<<<<<<< HEAD
	if ctx.asset:
		out.current_asset_value = flt(
			get_asset_value_after_depreciation(ctx.asset, finance_book=ctx.finance_book)
		)
		out.asset_value = get_value_after_depreciation_on_disposal_date(
			ctx.asset, ctx.posting_date, finance_book=ctx.finance_book
=======
	if args.asset:
		out.current_asset_value = flt(
			get_asset_value_after_depreciation(args.asset, finance_book=args.finance_book)
		)
		out.asset_value = get_value_after_depreciation_on_disposal_date(
			args.asset, args.posting_date, finance_book=args.finance_book
>>>>>>> 7c4cf3e834 (Favicon.svg)
		)
	else:
		out.current_asset_value = 0
		out.asset_value = 0

	# Account
	if asset_details.item_code:
		out.fixed_asset_account = get_asset_category_account(
<<<<<<< HEAD
			"fixed_asset_account", item=asset_details.item_code, company=ctx.company
=======
			"fixed_asset_account", item=asset_details.item_code, company=args.company
>>>>>>> 7c4cf3e834 (Favicon.svg)
		)
	else:
		out.fixed_asset_account = None

	# Cost Center
	if asset_details.item_code:
		item = frappe.get_cached_doc("Item", asset_details.item_code)
<<<<<<< HEAD
		item_defaults = get_item_defaults(item.name, ctx.company)
		item_group_defaults = get_item_group_defaults(item.name, ctx.company)
		brand_defaults = get_brand_defaults(item.name, ctx.company)
		out.cost_center = get_default_cost_center(ctx, item_defaults, item_group_defaults, brand_defaults)
=======
		item_defaults = get_item_defaults(item.name, args.company)
		item_group_defaults = get_item_group_defaults(item.name, args.company)
		brand_defaults = get_brand_defaults(item.name, args.company)
		out.cost_center = get_default_cost_center(args, item_defaults, item_group_defaults, brand_defaults)
>>>>>>> 7c4cf3e834 (Favicon.svg)
	return out


@frappe.whitelist()
<<<<<<< HEAD
@erpnext.normalize_ctx_input(ItemDetailsCtx)
def get_service_item_details(ctx):
	out = frappe._dict()

	item = frappe._dict()
	if ctx.item_code:
		item = frappe.get_cached_doc("Item", ctx.item_code)

	out.item_name = item.item_name
	out.qty = flt(ctx.qty) or 1
	out.uom = item.purchase_uom or item.stock_uom

	item_defaults = get_item_defaults(item.name, ctx.company)
	item_group_defaults = get_item_group_defaults(item.name, ctx.company)
	brand_defaults = get_brand_defaults(item.name, ctx.company)

	out.expense_account = get_default_expense_account(ctx, item_defaults, item_group_defaults, brand_defaults)
	out.cost_center = get_default_cost_center(ctx, item_defaults, item_group_defaults, brand_defaults)
=======
def get_service_item_details(args):
	if isinstance(args, str):
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
	out.cost_center = get_default_cost_center(args, item_defaults, item_group_defaults, brand_defaults)
>>>>>>> 7c4cf3e834 (Favicon.svg)

	return out


@frappe.whitelist()
<<<<<<< HEAD
def get_items_tagged_to_wip_composite_asset(params):
	if isinstance(params, str):
		params = json.loads(params)

=======
def get_items_tagged_to_wip_composite_asset(asset):
>>>>>>> 7c4cf3e834 (Favicon.svg)
	fields = [
		"item_code",
		"item_name",
		"batch_no",
		"serial_no",
		"stock_qty",
		"stock_uom",
		"warehouse",
		"cost_center",
		"qty",
		"valuation_rate",
		"amount",
		"is_fixed_asset",
<<<<<<< HEAD
		"parent as purchase_receipt",
		"name as purchase_receipt_item",
	]

	pr_items = frappe.get_all(
		"Purchase Receipt Item",
		filters={"wip_composite_asset": params.get("target_asset"), "docstatus": 1},
		fields=fields,
=======
		"parent",
	]

	pr_items = frappe.get_all(
		"Purchase Receipt Item", filters={"wip_composite_asset": asset, "docstatus": 1}, fields=fields
>>>>>>> 7c4cf3e834 (Favicon.svg)
	)

	stock_items = []
	asset_items = []
<<<<<<< HEAD

	for d in pr_items:
		if not d.is_fixed_asset:
			stock_item = process_stock_item(d)
			if stock_item:
				stock_items.append(stock_item)
		else:
			asset_item = process_fixed_asset(d)
			if asset_item:
				asset_items.append(asset_item)

	return stock_items, asset_items


def process_stock_item(d):
	stock_capitalized = frappe.db.exists(
		"Asset Capitalization Stock Item",
		{
			"purchase_receipt_item": d.purchase_receipt_item,
			"parentfield": "stock_items",
			"parenttype": "Asset Capitalization",
			"docstatus": 1,
		},
	)

	if stock_capitalized:
		return None

	stock_item_data = frappe._dict(d)
	stock_item_data.purchase_receipt_item = d.purchase_receipt_item
	return stock_item_data


def process_fixed_asset(d):
	asset_details = frappe.db.get_value(
		"Asset",
		{
			"item_code": d.item_code,
			"purchase_receipt": d.purchase_receipt,
			"status": ("not in", ["Draft", "Scrapped", "Sold", "Capitalized"]),
		},
		["name as asset", "asset_name", "company"],
		as_dict=1,
	)

	if asset_details:
		asset_details.update(d)
		asset_details.update(get_consumed_asset_details(asset_details))
		d.update(asset_details)

		return frappe._dict(d)
	return None
=======
	for d in pr_items:
		if not d.is_fixed_asset:
			stock_items.append(frappe._dict(d))
		else:
			asset_details = frappe.db.get_value(
				"Asset",
				{"item_code": d.item_code, "purchase_receipt": d.parent},
				["name as asset", "asset_name"],
				as_dict=1,
			)
			d.update(asset_details)
			asset_items.append(frappe._dict(d))

	return stock_items, asset_items
>>>>>>> 7c4cf3e834 (Favicon.svg)
