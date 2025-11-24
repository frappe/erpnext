# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt, get_link_to_form, getdate, nowdate

import erpnext
from erpnext.accounts.utils import get_account_currency
from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.controllers.subcontracting_controller import SubcontractingController
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import get_default_cost_center, get_default_expense_account
from erpnext.stock.stock_ledger import get_valuation_rate


class BOMQuantityError(frappe.ValidationError):
	pass


class SubcontractingReceipt(SubcontractingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.landed_cost_taxes_and_charges.landed_cost_taxes_and_charges import (
			LandedCostTaxesandCharges,
		)
		from erpnext.subcontracting.doctype.subcontracting_receipt_item.subcontracting_receipt_item import (
			SubcontractingReceiptItem,
		)
		from erpnext.subcontracting.doctype.subcontracting_receipt_supplied_item.subcontracting_receipt_supplied_item import (
			SubcontractingReceiptSuppliedItem,
		)

		additional_costs: DF.Table[LandedCostTaxesandCharges]
		address_display: DF.TextEditor | None
		amended_from: DF.Link | None
		auto_repeat: DF.Link | None
		bill_date: DF.Date | None
		bill_no: DF.Data | None
		billing_address: DF.Link | None
		billing_address_display: DF.TextEditor | None
		company: DF.Link
		contact_display: DF.SmallText | None
		contact_email: DF.SmallText | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		cost_center: DF.Link | None
		distribute_additional_costs_based_on: DF.Literal["Qty", "Amount"]
		in_words: DF.Data | None
		instructions: DF.SmallText | None
		is_return: DF.Check
		items: DF.Table[SubcontractingReceiptItem]
		language: DF.Data | None
		letter_head: DF.Link | None
		lr_date: DF.Date | None
		lr_no: DF.Data | None
		naming_series: DF.Literal["MAT-SCR-.YYYY.-", "MAT-SCR-RET-.YYYY.-"]
		per_returned: DF.Percent
		posting_date: DF.Date
		posting_time: DF.Time
		project: DF.Link | None
		range: DF.Data | None
		rejected_warehouse: DF.Link | None
		remarks: DF.SmallText | None
		represents_company: DF.Link | None
		return_against: DF.Link | None
		select_print_heading: DF.Link | None
		set_posting_time: DF.Check
		set_warehouse: DF.Link | None
		shipping_address: DF.Link | None
		shipping_address_display: DF.TextEditor | None
		status: DF.Literal["", "Draft", "Completed", "Return", "Return Issued", "Cancelled", "Closed"]
		supplied_items: DF.Table[SubcontractingReceiptSuppliedItem]
		supplier: DF.Link
		supplier_address: DF.Link | None
		supplier_delivery_note: DF.Data | None
		supplier_name: DF.Data | None
		supplier_warehouse: DF.Link | None
		title: DF.Data | None
		total: DF.Currency
		total_additional_costs: DF.Currency
		total_qty: DF.Float
		transporter_name: DF.Data | None
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.status_updater = [
			{
				"target_dt": "Subcontracting Order Item",
				"join_field": "subcontracting_order_item",
				"target_field": "received_qty",
				"target_parent_dt": "Subcontracting Order",
				"target_parent_field": "per_received",
				"target_ref_field": "qty",
				"source_dt": "Subcontracting Receipt Item",
				"source_field": "received_qty",
				"percent_join_field": "subcontracting_order",
				"overflow_type": "receipt",
			},
		]

	def onload(self):
		self.set_onload(
			"backflush_based_on",
			frappe.db.get_single_value("Buying Settings", "backflush_raw_materials_of_subcontract_based_on"),
		)

	def before_validate(self):
		super().before_validate()
		self.validate_items_qty()
		self.set_items_bom()
		self.set_items_cost_center()

		if self.company:
			default_expense_account = self.get_company_default(
				"default_expense_account", ignore_validation=True
			)
			self.set_service_expense_account(default_expense_account)
			self.set_expense_account_for_subcontracted_items(default_expense_account)

	def validate(self):
		self.reset_supplied_items()
		self.validate_posting_time()

		if not self.get("is_return"):
			self.validate_inspection()

		if getdate(self.posting_date) > getdate(nowdate()):
			frappe.throw(_("Posting Date cannot be future date"))

		super().validate()

		if self.is_new() and self.get("_action") == "save" and not frappe.in_test:
			self.get_scrap_items()

		self.set_missing_values()

		if self.get("_action") == "submit":
			self.validate_scrap_items()
			self.validate_accepted_warehouse()
			self.validate_rejected_warehouse()

		self.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.reset_default_field_value("rejected_warehouse", "items", "rejected_warehouse")
		self.get_current_stock()

		self.set_supplied_items_expense_account()
		self.set_supplied_items_cost_center()

	def on_submit(self):
		self.validate_closed_subcontracting_order()
		self.validate_available_qty_for_consumption()
		self.validate_bom_required_qty()
		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.set_subcontracting_order_status(update_bin=False)
		self.set_consumed_qty_in_subcontract_order()

		for table_name in ["items", "supplied_items"]:
			self.make_bundle_using_old_serial_batch_fields(table_name)

		self.update_stock_reservation_entries()
		self.update_stock_ledger()
		self.make_gl_entries()
		self.repost_future_sle_and_gle()
		self.update_status()
		self.auto_create_purchase_receipt()
		self.update_job_card()

	def on_update(self):
		for table_field in ["items", "supplied_items"]:
			if self.get(table_field):
				self.set_serial_and_batch_bundle(table_field)

	def on_cancel(self):
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Stock Ledger Entry",
			"Repost Item Valuation",
			"Serial and Batch Bundle",
		)
		self.validate_closed_subcontracting_order()
		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.set_consumed_qty_in_subcontract_order()
		self.set_subcontracting_order_status(update_bin=False)
		self.update_stock_ledger()
		self.update_stock_reservation_entries()
		self.make_gl_entries_on_cancel()
		self.repost_future_sle_and_gle()
		self.update_status()
		self.delete_auto_created_batches()
		self.update_job_card()

	@frappe.whitelist()
	def reset_raw_materials(self):
		self.supplied_items = []
		self.flags.reset_raw_materials = True
		self.create_raw_materials_supplied_or_received()

	def validate_closed_subcontracting_order(self):
		for item in self.items:
			if item.subcontracting_order:
				check_on_hold_or_closed_status("Subcontracting Order", item.subcontracting_order)

	def update_job_card(self):
		for row in self.get("items"):
			if row.job_card:
				doc = frappe.get_doc("Job Card", row.job_card)
				doc.set_manufactured_qty()

	def set_service_expense_account(self, default_expense_account):
		for row in self.get("items"):
			if not row.service_expense_account and row.purchase_order_item:
				service_item = frappe.db.get_value(
					"Purchase Order Item", row.purchase_order_item, "item_code"
				)

				if service_item:
					if default := (
						get_item_defaults(service_item, self.company)
						or get_item_group_defaults(service_item, self.company)
						or get_brand_defaults(service_item, self.company)
					):
						if service_expense_account := default.get("expense_account"):
							row.service_expense_account = service_expense_account

			if not row.service_expense_account:
				row.service_expense_account = default_expense_account

	def set_expense_account_for_subcontracted_items(self, default_expense_account):
		for row in self.get("items"):
			if not row.expense_account:
				if default := (
					get_item_defaults(row.item_code, self.company)
					or get_item_group_defaults(row.item_code, self.company)
					or get_brand_defaults(row.item_code, self.company)
				):
					if expense_account := default.get("expense_account"):
						row.expense_account = expense_account

			if not row.expense_account:
				row.expense_account = default_expense_account

	def get_manufactured_qty(self, job_card):
		table = frappe.qb.DocType("Subcontracting Receipt Item")
		query = (
			frappe.qb.from_(table)
			.select(Sum(table.qty))
			.where((table.job_card == job_card) & (table.docstatus == 1))
		)

		qty = query.run()[0][0] or 0.0
		return flt(qty)

	def validate_items_qty(self):
		for item in self.items:
			if not (item.qty or item.rejected_qty):
				frappe.throw(
					_("Row {0}: Accepted Qty and Rejected Qty can't be zero at the same time.").format(
						item.idx
					)
				)

	def set_items_bom(self):
		if self.is_return:
			for item in self.items:
				if not item.bom:
					item.bom = frappe.db.get_value(
						"Subcontracting Receipt Item",
						{"name": item.subcontracting_receipt_item, "parent": self.return_against},
						"bom",
					)
		else:
			for item in self.items:
				if not item.bom:
					item.bom = frappe.db.get_value(
						"Subcontracting Order Item",
						{"name": item.subcontracting_order_item, "parent": item.subcontracting_order},
						"bom",
					)

	def set_items_cost_center(self):
		if self.company:
			cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

			for item in self.items:
				if not item.cost_center:
					item.cost_center = cost_center

	def set_supplied_items_cost_center(self):
		for item in self.supplied_items:
			if not item.cost_center:
				item.cost_center = get_default_cost_center(
					{"project": self.project},
					get_item_defaults(item.rm_item_code, self.company),
					get_item_group_defaults(item.rm_item_code, self.company),
					get_brand_defaults(item.rm_item_code, self.company),
					self.company,
				)

	def set_supplied_items_expense_account(self):
		for item in self.supplied_items:
			if not item.expense_account:
				item.expense_account = get_default_expense_account(
					frappe._dict(
						{
							"expense_account": self.get_company_default(
								"default_expense_account", ignore_validation=True
							)
						}
					),
					get_item_defaults(item.rm_item_code, self.company),
					get_item_group_defaults(item.rm_item_code, self.company),
					get_brand_defaults(item.rm_item_code, self.company),
				)

	def reset_supplied_items(self):
		if (
			frappe.db.get_single_value("Buying Settings", "backflush_raw_materials_of_subcontract_based_on")
			== "BOM"
			and self.supplied_items
		):
			if not any(
				item.serial_and_batch_bundle or item.batch_no or item.serial_no
				for item in self.supplied_items
			):
				self.supplied_items = []
			else:
				self.update_rate_for_supplied_items()

	@frappe.whitelist()
	def get_scrap_items(self, recalculate_rate=False):
		self.remove_scrap_items()

		for item in list(self.items):
			if item.bom:
				bom = frappe.get_doc("BOM", item.bom)
				for scrap_item in bom.scrap_items:
					qty = flt(item.qty) * (flt(scrap_item.stock_qty) / flt(bom.quantity))
					rate = (
						get_valuation_rate(
							scrap_item.item_code,
							self.set_warehouse,
							self.doctype,
							self.name,
							currency=erpnext.get_company_currency(self.company),
							company=self.company,
						)
						or scrap_item.rate
					)
					self.append(
						"items",
						{
							"is_scrap_item": 1,
							"reference_name": item.name,
							"item_code": scrap_item.item_code,
							"item_name": scrap_item.item_name,
							"qty": qty,
							"stock_uom": scrap_item.stock_uom,
							"rate": rate,
							"rm_cost_per_qty": 0,
							"service_cost_per_qty": 0,
							"additional_cost_per_qty": 0,
							"scrap_cost_per_qty": 0,
							"amount": qty * rate,
							"warehouse": self.set_warehouse,
							"rejected_warehouse": self.rejected_warehouse,
						},
					)

		if recalculate_rate:
			self.calculate_additional_costs()
			self.calculate_items_qty_and_amount()

	def remove_scrap_items(self, recalculate_rate=False):
		for item in list(self.items):
			if item.is_scrap_item:
				self.remove(item)
			else:
				item.scrap_cost_per_qty = 0

		if recalculate_rate:
			self.calculate_items_qty_and_amount()

	@frappe.whitelist()
	def set_missing_values(self):
		self.set_available_qty_for_consumption()
		self.calculate_additional_costs()
		self.calculate_items_qty_and_amount()

	def set_available_qty_for_consumption(self):
		supplied_items_details = {}

		sco_supplied_item = frappe.qb.DocType("Subcontracting Order Supplied Item")
		for item in self.get("items"):
			supplied_items = (
				frappe.qb.from_(sco_supplied_item)
				.select(
					sco_supplied_item.rm_item_code,
					sco_supplied_item.reference_name,
					(sco_supplied_item.total_supplied_qty - sco_supplied_item.consumed_qty).as_(
						"available_qty"
					),
				)
				.where(
					(sco_supplied_item.parent == item.subcontracting_order)
					& (sco_supplied_item.main_item_code == item.item_code)
					& (sco_supplied_item.reference_name == item.subcontracting_order_item)
				)
			).run(as_dict=True)

			if supplied_items:
				supplied_items_details[item.name] = {}

				for supplied_item in supplied_items:
					if supplied_item.rm_item_code not in supplied_items_details[item.name]:
						supplied_items_details[item.name][supplied_item.rm_item_code] = 0.0

					supplied_items_details[item.name][
						supplied_item.rm_item_code
					] += supplied_item.available_qty
		else:
			for item in self.get("supplied_items"):
				item.available_qty_for_consumption = supplied_items_details.get(item.reference_name, {}).get(
					item.rm_item_code, 0
				)

	def calculate_items_qty_and_amount(self):
		rm_cost_map = {}
		for item in self.get("supplied_items") or []:
			item.amount = flt(item.consumed_qty) * flt(item.rate)

			if item.reference_name in rm_cost_map:
				rm_cost_map[item.reference_name] += item.amount
			else:
				rm_cost_map[item.reference_name] = item.amount

		scrap_cost_map = {}
		for item in self.get("items") or []:
			if item.is_scrap_item:
				item.amount = flt(item.qty) * flt(item.rate)

				if item.reference_name in scrap_cost_map:
					scrap_cost_map[item.reference_name] += item.amount
				else:
					scrap_cost_map[item.reference_name] = item.amount

		total_qty = total_amount = 0
		for item in self.get("items") or []:
			if not item.is_scrap_item:
				if item.qty:
					if item.name in rm_cost_map:
						item.rm_supp_cost = rm_cost_map[item.name]
						item.rm_cost_per_qty = item.rm_supp_cost / item.qty
						rm_cost_map.pop(item.name)

					if item.name in scrap_cost_map:
						item.scrap_cost_per_qty = scrap_cost_map[item.name] / item.qty
						scrap_cost_map.pop(item.name)
					else:
						item.scrap_cost_per_qty = 0

				lcv_cost_per_qty = 0.0
				if item.landed_cost_voucher_amount:
					lcv_cost_per_qty = item.landed_cost_voucher_amount / item.qty

				item.rate = (
					flt(item.rm_cost_per_qty)
					+ flt(item.service_cost_per_qty)
					+ flt(item.additional_cost_per_qty)
					+ flt(lcv_cost_per_qty)
					- flt(item.scrap_cost_per_qty)
				)

			item.received_qty = flt(item.qty) + flt(item.rejected_qty)
			item.amount = flt(item.qty) * flt(item.rate)

			total_qty += flt(item.qty)
			total_amount += item.amount
		else:
			self.total_qty = total_qty
			self.total = total_amount

	def validate_scrap_items(self):
		for item in self.items:
			if item.is_scrap_item:
				if not item.qty:
					frappe.throw(
						_("Row #{0}: Scrap Item Qty cannot be zero").format(item.idx),
					)

				if item.rejected_qty:
					frappe.throw(
						_("Row #{0}: Rejected Qty cannot be set for Scrap Item {1}.").format(
							item.idx, frappe.bold(item.item_code)
						),
					)

				if not item.reference_name:
					frappe.throw(
						_("Row #{0}: Finished Good reference is mandatory for Scrap Item {1}.").format(
							item.idx, frappe.bold(item.item_code)
						),
					)

	def validate_accepted_warehouse(self):
		for item in self.get("items"):
			if flt(item.qty) and not item.warehouse:
				if self.set_warehouse:
					item.warehouse = self.set_warehouse
				else:
					frappe.throw(
						_("Row #{0}: Accepted Warehouse is mandatory for the accepted Item {1}").format(
							item.idx, item.item_code
						)
					)

			if item.get("warehouse") and (item.get("warehouse") == item.get("rejected_warehouse")):
				frappe.throw(
					_("Row #{0}: Accepted Warehouse and Rejected Warehouse cannot be same").format(item.idx)
				)

	def validate_available_qty_for_consumption(self):
		if (
			frappe.db.get_single_value("Buying Settings", "backflush_raw_materials_of_subcontract_based_on")
			== "BOM"
		):
			return

		for item in self.get("supplied_items"):
			precision = item.precision("consumed_qty")
			if (
				item.available_qty_for_consumption
				and flt(item.available_qty_for_consumption, precision) - flt(item.consumed_qty, precision) < 0
			):
				msg = _(
					"""Row {0}: Consumed Qty {1} {2} must be less than or equal to Available Qty For Consumption
					{3} {4} in Consumed Items Table."""
				).format(
					item.idx,
					flt(item.consumed_qty, precision),
					item.stock_uom,
					flt(item.available_qty_for_consumption, precision),
					item.stock_uom,
				)

				frappe.throw(msg)

	def validate_bom_required_qty(self):
		if (
			frappe.db.get_single_value("Buying Settings", "backflush_raw_materials_of_subcontract_based_on")
			== "Material Transferred for Subcontract"
		) and not (frappe.db.get_single_value("Buying Settings", "validate_consumed_qty")):
			return

		rm_consumed_dict = self.get_rm_wise_consumed_qty()

		for row in self.items:
			precision = row.precision("qty")
			for bom_item in self._get_materials_from_bom(
				row.item_code, row.bom, row.get("include_exploded_items")
			):
				required_qty = flt(
					bom_item.qty_consumed_per_unit * row.qty * row.conversion_factor, precision
				)
				consumed_qty = rm_consumed_dict.get(bom_item.rm_item_code, 0)
				diff = flt(consumed_qty, precision) - flt(required_qty, precision)

				if diff < 0:
					msg = _(
						"""Additional {0} {1} of item {2} required as per BOM to complete this transaction"""
					).format(
						frappe.bold(abs(diff)),
						frappe.bold(bom_item.stock_uom),
						frappe.bold(bom_item.rm_item_code),
					)

					frappe.throw(
						msg,
						exc=BOMQuantityError,
					)

	def get_rm_wise_consumed_qty(self):
		rm_dict = defaultdict(float)

		for row in self.supplied_items:
			rm_dict[row.rm_item_code] += row.consumed_qty

		return rm_dict

	def update_status_updater_args(self):
		if cint(self.is_return):
			self.status_updater.extend(
				[
					{
						"source_dt": "Subcontracting Receipt Item",
						"target_dt": "Subcontracting Order Item",
						"join_field": "subcontracting_order_item",
						"target_field": "returned_qty",
						"source_field": "-1 * qty",
						"extra_cond": """ and exists (select name from `tabSubcontracting Receipt`
						where name=`tabSubcontracting Receipt Item`.parent and is_return=1)""",
					},
					{
						"source_dt": "Subcontracting Receipt Item",
						"target_dt": "Subcontracting Receipt Item",
						"join_field": "subcontracting_receipt_item",
						"target_field": "returned_qty",
						"target_parent_dt": "Subcontracting Receipt",
						"target_parent_field": "per_returned",
						"target_ref_field": "received_qty",
						"source_field": "-1 * received_qty",
						"percent_join_field_parent": "return_against",
					},
				]
			)

	def update_status(self, status=None, update_modified=False):
		if not status:
			if self.docstatus == 0:
				status = "Draft"
			elif self.docstatus == 1:
				status = "Completed"

				if self.is_return:
					status = "Return"
				elif self.per_returned == 100:
					status = "Return Issued"

			elif self.docstatus == 2:
				status = "Cancelled"

			if self.is_return:
				frappe.get_doc("Subcontracting Receipt", self.return_against).update_status(
					update_modified=update_modified
				)

		if status:
			frappe.db.set_value(
				"Subcontracting Receipt", self.name, "status", status, update_modified=update_modified
			)

	def get_gl_entries(self, inventory_account_map=None):
		from erpnext.accounts.general_ledger import process_gl_map

		if not erpnext.is_perpetual_inventory_enabled(self.company):
			return []

		gl_entries = []
		self.make_item_gl_entries(gl_entries, inventory_account_map)
		self.make_item_gl_entries_for_lcv(gl_entries, inventory_account_map)

		return process_gl_map(gl_entries, from_repost=frappe.flags.through_repost_item_valuation)

	def make_item_gl_entries(self, gl_entries, inventory_account_map=None):
		warehouse_with_no_account = []

		supplied_items_details = frappe._dict()
		for item in self.supplied_items:
			supplied_items_details.setdefault(item.reference_name, []).append(
				frappe._dict(
					{
						"item_code": item.rm_item_code,
						"amount": item.amount,
						"expense_account": item.expense_account,
						"cost_center": item.cost_center,
					}
				)
			)

		for item in self.items:
			if flt(item.rate) and flt(item.qty):
				_inv_dict = self.get_inventory_account_dict(item, inventory_account_map)

				if _inv_dict.get("account"):
					stock_value_diff = frappe.db.get_value(
						"Stock Ledger Entry",
						{
							"voucher_type": "Subcontracting Receipt",
							"voucher_no": self.name,
							"voucher_detail_no": item.name,
							"warehouse": item.warehouse,
							"is_cancelled": 0,
						},
						"stock_value_difference",
					)

					remarks = self.get("remarks") or _("Accounting Entry for Stock")

					# Accepted Warehouse Account (Debit)
					self.add_gl_entry(
						gl_entries=gl_entries,
						account=_inv_dict["account"],
						cost_center=item.cost_center,
						debit=stock_value_diff,
						credit=0.0,
						remarks=remarks,
						against_account=item.expense_account,
						account_currency=_inv_dict["account_currency"],
						project=item.project,
						item=item,
					)

					service_cost = flt(
						item.service_cost_per_qty, item.precision("service_cost_per_qty")
					) * flt(item.qty, item.precision("qty"))
					# Expense Account (Credit)
					self.add_gl_entry(
						gl_entries=gl_entries,
						account=item.expense_account,
						cost_center=item.cost_center,
						debit=0.0,
						credit=flt(stock_value_diff) - service_cost,
						remarks=remarks,
						against_account=_inv_dict["account"],
						account_currency=get_account_currency(item.expense_account),
						project=item.project,
						item=item,
					)

					service_account = item.service_expense_account or item.expense_account
					# Expense Account (Credit)
					self.add_gl_entry(
						gl_entries=gl_entries,
						account=service_account,
						cost_center=item.cost_center,
						debit=0.0,
						credit=service_cost,
						remarks=remarks,
						against_account=_inv_dict["account"],
						account_currency=get_account_currency(service_account),
						project=item.project,
						item=item,
					)

					if flt(item.rm_supp_cost):
						for rm_item in supplied_items_details.get(item.name):
							_inv_dict = self.get_inventory_account_dict(
								rm_item, inventory_account_map, "supplier_warehouse"
							)

							# Supplier Warehouse Account (Credit)
							self.add_gl_entry(
								gl_entries=gl_entries,
								account=_inv_dict.get("account"),
								cost_center=rm_item.cost_center or item.cost_center,
								debit=0.0,
								credit=flt(rm_item.amount),
								remarks=remarks,
								against_account=rm_item.expense_account or item.expense_account,
								account_currency=_inv_dict.get("account_currency"),
								project=item.project,
								item=item,
							)
							# Expense Account (Debit)
							self.add_gl_entry(
								gl_entries=gl_entries,
								account=rm_item.expense_account or item.expense_account,
								cost_center=rm_item.cost_center or item.cost_center,
								debit=flt(rm_item.amount),
								credit=0.0,
								remarks=remarks,
								against_account=_inv_dict.get("account"),
								account_currency=get_account_currency(item.expense_account),
								project=item.project,
								item=item,
							)

					# Expense Account (Debit)
					if item.additional_cost_per_qty:
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=item.expense_account,
							cost_center=self.cost_center or self.get_company_default("cost_center"),
							debit=item.qty * item.additional_cost_per_qty,
							credit=0.0,
							remarks=remarks,
							against_account=None,
							account_currency=get_account_currency(item.expense_account),
						)

					if divisional_loss := flt(item.amount - stock_value_diff, item.precision("amount")):
						loss_account = self.get_company_default(
							"stock_adjustment_account", ignore_validation=True
						)

						# Loss Account (Credit)
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=loss_account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=divisional_loss,
							remarks=remarks,
							against_account=item.expense_account,
							account_currency=get_account_currency(loss_account),
							project=item.project,
							item=item,
						)
						# Expense Account (Debit)
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=item.expense_account,
							cost_center=item.cost_center,
							debit=divisional_loss,
							credit=0.0,
							remarks=remarks,
							against_account=loss_account,
							account_currency=get_account_currency(item.expense_account),
							project=item.project,
							item=item,
						)
				elif (
					item.warehouse not in warehouse_with_no_account
					or item.rejected_warehouse not in warehouse_with_no_account
				):
					warehouse_with_no_account.append(item.warehouse)

		for row in self.additional_costs:
			credit_amount = (
				flt(row.base_amount)
				if (row.base_amount or row.account_currency != self.company_currency)
				else flt(row.amount)
			)

			# Additional Cost Expense Account (Credit)
			self.add_gl_entry(
				gl_entries=gl_entries,
				account=row.expense_account,
				cost_center=self.cost_center or self.get_company_default("cost_center"),
				debit=0.0,
				credit=credit_amount,
				remarks=remarks,
				against_account=None,
				account_currency=get_account_currency(row.expense_account),
			)

		if warehouse_with_no_account:
			frappe.msgprint(
				_("No accounting entries for the following warehouses")
				+ ": \n"
				+ "\n".join(warehouse_with_no_account)
			)

	def make_item_gl_entries_for_lcv(self, gl_entries, inventory_account_map):
		landed_cost_entries = self.get_item_account_wise_lcv_entries()

		if not landed_cost_entries:
			return

		for item in self.items:
			if item.landed_cost_voucher_amount and landed_cost_entries:
				remarks = _("Accounting Entry for Landed Cost Voucher for SCR {0}").format(self.name)
				if (item.item_code, item.name) in landed_cost_entries:
					_inv_dict = self.get_inventory_account_dict(item, inventory_account_map)

					for account, amount in landed_cost_entries[(item.item_code, item.name)].items():
						account_currency = get_account_currency(account)
						credit_amount = (
							flt(amount["base_amount"])
							if (amount["base_amount"] or account_currency != self.company_currency)
							else flt(amount["amount"])
						)

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=credit_amount,
							remarks=remarks,
							against_account=_inv_dict["account"],
							credit_in_account_currency=flt(amount["amount"]),
							account_currency=account_currency,
							project=item.project,
							item=item,
						)

						account_currency = get_account_currency(item.expense_account)

						# credit amount in negative to knock off the debit entry
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=item.expense_account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=credit_amount * -1,
							remarks=remarks,
							against_account=_inv_dict["account"],
							debit_in_account_currency=flt(amount["amount"]),
							account_currency=account_currency,
							project=item.project,
							item=item,
						)

	def auto_create_purchase_receipt(self):
		if frappe.db.get_single_value("Buying Settings", "auto_create_purchase_receipt"):
			make_purchase_receipt(self, save=True, notify=True)

	def has_reserved_stock(self):
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			get_sre_details_for_voucher,
		)

		for item in self.supplied_items:
			if get_sre_details_for_voucher("Subcontracting Order", item.subcontracting_order):
				return True

		return False


@frappe.whitelist()
def make_subcontract_return_against_rejected_warehouse(source_name):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Subcontracting Receipt", source_name, return_against_rejected_qty=True)


@frappe.whitelist()
def make_subcontract_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Subcontracting Receipt", source_name, target_doc)


@frappe.whitelist()
def make_purchase_receipt(source_name, target_doc=None, save=False, submit=False, notify=False):
	if isinstance(source_name, str):
		source_doc = frappe.get_doc("Subcontracting Receipt", source_name)
	else:
		source_doc = source_name

	if source_doc.is_return:
		return

	po_sr_item_dict = {}
	po_name = None
	for item in source_doc.items:
		if not item.purchase_order:
			continue

		if not po_name:
			po_name = item.purchase_order

		po_sr_item_dict[item.purchase_order_item] = {
			"qty": flt(item.qty),
			"rejected_qty": flt(item.rejected_qty),
			"warehouse": item.warehouse,
			"rejected_warehouse": item.rejected_warehouse,
			"subcontracting_receipt_item": item.name,
		}

	if not po_name:
		frappe.throw(
			_("Purchase Order Item reference is missing in Subcontracting Receipt {0}").format(
				source_doc.name
			)
		)

	def update_item(obj, target, source_parent):
		sr_item_details = po_sr_item_dict.get(obj.name)
		ratio = flt(obj.qty) / flt(obj.fg_item_qty)

		target.update(
			{
				"qty": ratio * sr_item_details["qty"],
				"rejected_qty": ratio * sr_item_details["rejected_qty"],
				"warehouse": sr_item_details["warehouse"],
				"rejected_warehouse": sr_item_details["rejected_warehouse"],
				"subcontracting_receipt_item": sr_item_details["subcontracting_receipt_item"],
			}
		)

	def post_process(source, target):
		target.set_missing_values()
		target.update(
			{
				"posting_date": source_doc.posting_date,
				"posting_time": source_doc.posting_time,
				"subcontracting_receipt": source_doc.name,
				"supplier_warehouse": source_doc.supplier_warehouse,
				"is_subcontracted": 1,
				"is_old_subcontracting_flow": 0,
				"currency": frappe.get_cached_value("Company", target.company, "default_currency"),
			}
		)

	target_doc = get_mapped_doc(
		"Purchase Order",
		po_name,
		{
			"Purchase Order": {
				"doctype": "Purchase Receipt",
				"field_map": {"supplier_warehouse": "supplier_warehouse"},
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Order Item": {
				"doctype": "Purchase Receipt Item",
				"field_map": {
					"name": "purchase_order_item",
					"parent": "purchase_order",
					"bom": "bom",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.name in po_sr_item_dict,
			},
			"Purchase Taxes and Charges": {
				"doctype": "Purchase Taxes and Charges",
				"reset_value": True,
				"condition": lambda doc: not doc.is_tax_withholding_account,
			},
		},
		postprocess=post_process,
	)

	if not target_doc.get("items"):
		add_po_items_to_pr(source_doc, target_doc)

	if (save or submit) and frappe.has_permission(target_doc.doctype, "create"):
		target_doc.save()

		if submit and frappe.has_permission(target_doc.doctype, "submit", target_doc):
			try:
				target_doc.submit()
			except Exception as e:
				target_doc.add_comment("Comment", _("Submit Action Failed") + "<br><br>" + str(e))

		if notify:
			frappe.msgprint(
				_("Purchase Receipt {0} created.").format(
					get_link_to_form(target_doc.doctype, target_doc.name)
				),
				indicator="green",
				alert=True,
			)

	return target_doc


def add_po_items_to_pr(scr_doc, target_doc):
	fg_items = {(item.item_code, item.purchase_order): item.qty for item in scr_doc.items}

	for (item_code, po_name), fg_qty in fg_items.items():
		po_doc = frappe.get_doc("Purchase Order", po_name)
		for item in po_doc.items:
			if item.fg_item != item_code:
				continue

			qty = (item.stock_qty - item.received_qty) * fg_qty / item.fg_item_qty
			if qty:
				target_doc.append(
					"items",
					{
						"item_code": item.item_code,
						"item_name": item.item_name,
						"description": item.description,
						"qty": qty,
						"rate": item.rate,
						"warehouse": item.warehouse,
						"purchase_order": item.parent,
						"purchase_order_item": item.name,
					},
				)
