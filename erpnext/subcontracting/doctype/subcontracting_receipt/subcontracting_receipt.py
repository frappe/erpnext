# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt, get_link_to_form, getdate, nowdate

import erpnext
from erpnext.accounts.utils import get_account_currency
from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.controllers.subcontracting_controller import SubcontractingController
from erpnext.stock.stock_ledger import get_valuation_rate


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
		address_display: DF.SmallText | None
		amended_from: DF.Link | None
		auto_repeat: DF.Link | None
		bill_date: DF.Date | None
		bill_no: DF.Data | None
		billing_address: DF.Link | None
		billing_address_display: DF.SmallText | None
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
		shipping_address_display: DF.SmallText | None
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
		self.set_items_expense_account()

	def validate(self):
		self.reset_supplied_items()
		self.validate_posting_time()

		if not self.get("is_return"):
			self.validate_inspection()

		if getdate(self.posting_date) > getdate(nowdate()):
			frappe.throw(_("Posting Date cannot be future date"))

		super().validate()

		if self.is_new() and self.get("_action") == "save" and not frappe.flags.in_test:
			self.get_scrap_items()

		self.set_missing_values()

		if self.get("_action") == "submit":
			self.validate_scrap_items()
			self.validate_accepted_warehouse()
			self.validate_rejected_warehouse()

		self.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.reset_default_field_value("rejected_warehouse", "items", "rejected_warehouse")
		self.get_current_stock()

	def on_submit(self):
		self.validate_closed_subcontracting_order()
		self.validate_available_qty_for_consumption()
		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.set_subcontracting_order_status()
		self.set_consumed_qty_in_subcontract_order()

		for table_name in ["items", "supplied_items"]:
			self.make_bundle_using_old_serial_batch_fields(table_name)
		self.update_stock_ledger()
		self.make_gl_entries()
		self.repost_future_sle_and_gle()
		self.update_status()
		self.auto_create_purchase_receipt()

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
		self.set_subcontracting_order_status()
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()
		self.repost_future_sle_and_gle()
		self.update_status()
		self.delete_auto_created_batches()

	@frappe.whitelist()
	def reset_raw_materials(self):
		self.supplied_items = []
		self.create_raw_materials_supplied()

	def validate_closed_subcontracting_order(self):
		for item in self.items:
			if item.subcontracting_order:
				check_on_hold_or_closed_status("Subcontracting Order", item.subcontracting_order)

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

	def set_items_expense_account(self):
		if self.company:
			expense_account = self.get_company_default("default_expense_account", ignore_validation=True)

			for item in self.items:
				if not item.expense_account:
					item.expense_account = expense_account

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

				item.rate = (
					flt(item.rm_cost_per_qty)
					+ flt(item.service_cost_per_qty)
					+ flt(item.additional_cost_per_qty)
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
				msg = f"""Row {item.idx}: Consumed Qty {flt(item.consumed_qty, precision)}
					must be less than or equal to Available Qty For Consumption
					{flt(item.available_qty_for_consumption, precision)}
					in Consumed Items Table."""

				frappe.throw(_(msg))

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

	def get_gl_entries(self, warehouse_account=None):
		from erpnext.accounts.general_ledger import process_gl_map

		if not erpnext.is_perpetual_inventory_enabled(self.company):
			return []

		gl_entries = []
		self.make_item_gl_entries(gl_entries, warehouse_account)

		return process_gl_map(gl_entries)

	def make_item_gl_entries(self, gl_entries, warehouse_account=None):
		warehouse_with_no_account = []

		for item in self.items:
			if flt(item.rate) and flt(item.qty):
				if warehouse_account.get(item.warehouse):
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

					accepted_warehouse_account = warehouse_account[item.warehouse]["account"]
					supplier_warehouse_account = warehouse_account.get(self.supplier_warehouse, {}).get(
						"account"
					)
					remarks = self.get("remarks") or _("Accounting Entry for Stock")

					# Accepted Warehouse Account (Debit)
					self.add_gl_entry(
						gl_entries=gl_entries,
						account=accepted_warehouse_account,
						cost_center=item.cost_center,
						debit=stock_value_diff,
						credit=0.0,
						remarks=remarks,
						against_account=item.expense_account,
						account_currency=get_account_currency(accepted_warehouse_account),
						project=item.project,
						item=item,
					)
					# Expense Account (Credit)
					self.add_gl_entry(
						gl_entries=gl_entries,
						account=item.expense_account,
						cost_center=item.cost_center,
						debit=0.0,
						credit=stock_value_diff,
						remarks=remarks,
						against_account=accepted_warehouse_account,
						account_currency=get_account_currency(item.expense_account),
						project=item.project,
						item=item,
					)

					if flt(item.rm_supp_cost) and supplier_warehouse_account:
						# Supplier Warehouse Account (Credit)
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=supplier_warehouse_account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=flt(item.rm_supp_cost),
							remarks=remarks,
							against_account=item.expense_account,
							account_currency=get_account_currency(supplier_warehouse_account),
							project=item.project,
							item=item,
						)
						# Expense Account (Debit)
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=item.expense_account,
							cost_center=item.cost_center,
							debit=flt(item.rm_supp_cost),
							credit=0.0,
							remarks=remarks,
							against_account=supplier_warehouse_account,
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

	def auto_create_purchase_receipt(self):
		if frappe.db.get_single_value("Buying Settings", "auto_create_purchase_receipt"):
			make_purchase_receipt(self, save=True, notify=True)


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
