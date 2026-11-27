# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import cint, comma_and, flt, get_link_to_form, getdate, nowdate

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions
from erpnext.accounts.utils import get_account_currency
from erpnext.controllers.sales_and_purchase_return import (
	get_already_returned_items,
	get_rate_for_return,
	validate_return,
)
from erpnext.controllers.subcontracting_controller import SubcontractingController
from erpnext.manufacturing.doctype.bom.bom import get_subcontracted_work_order_costs
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import get_default_cost_center, get_default_expense_account
from erpnext.stock.stock_ledger import get_valuation_rate
from erpnext.stock.utils import get_combine_datetime

ROW_BASED_CHARGE_TYPES = ("On Previous Row Amount", "On Previous Row Total")


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

		if self.docstatus == 1:
			self.set_onload(
				"allow_to_make_qc_after_submission",
				frappe.get_single_value(
					"Stock Settings", "allow_to_make_quality_inspection_after_purchase_or_delivery"
				),
			)
			if not self.is_return:
				self.set_onload("has_rejected_qty_to_return", self.has_rejected_qty_to_return())

	def has_rejected_qty_to_return(self) -> bool:
		rejected_rows = {row.name: row for row in self.items if flt(row.rejected_qty)}
		if not rejected_rows:
			return False

		item = frappe.qb.DocType("Subcontracting Receipt Item")
		returned_qty = frappe._dict(
			frappe.qb.from_(item)
			.select(item.subcontracting_receipt_item, Sum(item.qty))
			.where(
				item.subcontracting_receipt_item.isin(list(rejected_rows))
				& (item.return_qty_from_rejected_warehouse == 1)
				& (item.docstatus == 1)
			)
			.groupby(item.subcontracting_receipt_item)
			.run()
		)
		# return qty is negative
		return any(
			flt(row.rejected_qty + flt(returned_qty.get(name)), row.precision("rejected_qty")) > 0
			for name, row in rejected_rows.items()
		)

	def before_validate(self):
		self.save_inventory_dimensions()
		super().before_validate()
		self.validate_items_qty()
		self.set_items_bom()
		self.set_items_received_qty()
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
			self.validate_purchase_orders_share_terms()
			self.validate_additional_cost_accounts()
			self.validate_order_costs_are_not_repeated()

		if getdate(self.posting_date) > getdate(nowdate()):
			frappe.throw(_("Posting Date cannot be future date"))

		super().validate()
		# Secondary rows get a read-only qty from the BOM, so the user cannot round it.
		self.validate_item_stock_uom_is_integer(
			"item_code",
			["qty", "received_qty", "rejected_qty"],
			"Subcontracting Receipt Item",
			row_filter=lambda row: not (row.secondary_item_type or row.valuation_type),
		)

		self.set_missing_values()
		# after set_missing_values, so the secondary rates are computed from the same
		# calculated per-qty costs the Get Secondary Items button uses, and before
		# validate_return, so a return validates the rows it saves
		if self.is_new() and self.get("_action") == "save" and not frappe.in_test:
			self.get_secondary_items(recalculate_rate=True)

		self.validate_with_previous_doc()
		validate_return(self)
		self.validate_return_supplier_warehouse()

		if self.get("_action") == "submit":
			self.validate_returned_raw_materials()
			self.validate_secondary_items()
			self.validate_accepted_warehouse()
			self.validate_rejected_warehouse()

		self.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.reset_default_field_value("rejected_warehouse", "items", "rejected_warehouse")
		self.get_current_stock()

		self.set_supplied_items_expense_account()
		self.set_supplied_items_cost_center()
		self.set_supplied_items_inventory_dimensions()

		# SubcontractingController.validate() does not call super() for Subcontracting Receipt, so
		# the shared mandatory inventory dimension check must be invoked explicitly here. It runs
		# last so auto-populated supplied-item dimensions (set_supplied_items_inventory_dimensions)
		# are already in place.
		self.validate_inventory_dimension_mandatory()

	def validate_purchase_orders_share_terms(self):
		if not can_combine_purchase_orders(purchase_orders := get_purchase_orders(self)):
			frappe.throw(get_uncombinable_orders_message(purchase_orders), title=_("Cannot Combine Orders"))

	def validate_return_supplier_warehouse(self):
		if not (self.is_return and self.return_against):
			return

		original = frappe.db.get_value("Subcontracting Receipt", self.return_against, "supplier_warehouse")
		if self.supplier_warehouse != original:
			frappe.throw(
				_("{0} must be {1}, the same as in {2}").format(
					_(self.meta.get_label("supplier_warehouse")),
					frappe.bold(original),
					frappe.bold(self.return_against),
				),
				title=_("Warehouse Mismatch"),
			)

	def validate_with_previous_doc(self):
		super().validate_with_previous_doc(
			{
				"Subcontracting Order Item": {
					"ref_dn_field": "subcontracting_order_item",
					"compare_fields": [["project", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True,
				},
				"Purchase Order Item": {
					"ref_dn_field": "purchase_order_item",
					"compare_fields": [["project", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True,
				},
			}
		)

	def on_submit(self):
		self.validate_closed_subcontracting_order()
		self.validate_bom_required_qty()
		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.set_subcontracting_order_status(update_bin=False)
		self.set_consumed_qty_in_subcontract_order()
		self.make_bundle_for_sales_purchase_return()

		for table_name in ["items", "supplied_items"]:
			self.make_bundle_using_old_serial_batch_fields(table_name)

		self.validate_returned_serial_batches()
		self.update_stock_reservation_entries()
		self.update_stock_ledger()
		self.validate_consumed_batches()
		self.make_gl_entries()
		self.repost_future_sle_and_gle()
		self.update_status()
		self.auto_create_purchase_receipt()
		self.update_job_card()
		self.update_production_plan_received_qty()

	def validate_consumed_batches(self):
		bundles = frappe._dict(
			frappe.get_all(
				"Subcontracting Receipt Supplied Item",
				filters={"parent": self.name},
				fields=["name", "serial_and_batch_bundle"],
				as_list=True,
			)
		)
		for row in self.supplied_items:
			row.serial_and_batch_bundle = bundles.get(row.name) or row.serial_and_batch_bundle

		self.validate_outward_bundle_batches(
			check_expiry=False, rows=self.supplied_items, qty_field="consumed_qty"
		)

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
			"Quality Inspection",
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
		self.update_production_plan_received_qty()

	@frappe.whitelist()
	def reset_raw_materials(self):
		self.supplied_items = []
		self.flags.reset_raw_materials = True
		self.create_raw_materials_supplied_or_received()

	def validate_closed_subcontracting_order(self):
		self.check_for_on_hold_or_closed_status("Subcontracting Order", "subcontracting_order")

	def update_production_plan_received_qty(self):
		from erpnext.manufacturing.doctype.production_plan.production_plan import (
			update_subcontracted_received_qty,
		)

		update_subcontracted_received_qty(
			list({row.subcontracting_order_item for row in self.items if row.subcontracting_order_item})
		)

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
			# secondary rows are checked on submit, after a return has rebuilt them
			if item.secondary_item_type or item.valuation_type:
				continue

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

	def set_items_received_qty(self):
		"""Set before the supplied items are built from it."""
		for item in self.items:
			if item.bom:
				item.received_qty = self.get_qty_for_costing(item)

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

	def set_supplied_items_inventory_dimensions(self):
		if hasattr(self, "inventory_dimensions") and (inventory_dimensions := get_inventory_dimensions()):
			for item in self.supplied_items:
				key = (
					item.reference_name,
					item.rm_item_code,
					item.main_item_code,
					item.batch_no,
					item.serial_no,
				)

				for dimension in inventory_dimensions:
					dimension_values = self.inventory_dimensions.get(dimension.source_fieldname, {})
					if key in dimension_values:
						item.set(dimension.source_fieldname, dimension_values[key])

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

	def save_inventory_dimensions(self):
		if inventory_dimensions := get_inventory_dimensions():
			if not getattr(self, "inventory_dimensions", None):
				self.inventory_dimensions = {}

			for dimension in inventory_dimensions:
				self.inventory_dimensions[dimension.source_fieldname] = {
					(d.reference_name, d.rm_item_code, d.main_item_code, d.batch_no, d.serial_no): d.get(
						dimension.source_fieldname
					)
					for d in self.supplied_items
				}

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
	def get_secondary_items(self, recalculate_rate: bool | None = False):
		self.remove_secondary_items()

		original_rows = self.get_returned_receipt_rows()
		# rejected goods yield no secondary items
		rejected_return_rows = self.get_rejected_return_rows()
		for item in list(self.items):
			if item.bom and item.name not in rejected_return_rows:
				# finished goods returned so far, as a negative qty
				returned_qty = original_rows.get(item.subcontracting_receipt_item, {}).get("returned_qty")
				self.add_secondary_items_of_fg_row(item, -flt(returned_qty))

		self.link_returned_secondary_items(original_rows)
		self.set_remaining_secondary_qty(original_rows)
		self.remove_returned_secondary_rows_without_qty()

		if recalculate_rate:
			self.set_additional_costs_and_amounts()

	def get_returned_receipt_rows(self) -> dict:
		"""Rows of the receipt this return is against, by name."""
		if not (self.is_return and self.return_against):
			return {}

		return {
			row.name: row
			for row in frappe.get_all(
				"Subcontracting Receipt Item",
				filters={"parent": self.return_against},
				fields=[
					"name",
					"item_code",
					"qty",
					"received_qty",
					"process_loss_qty",
					"reference_name",
					"bom_secondary_item",
					"secondary_item_type",
					"valuation_type",
					"returned_qty",
				],
			)
		}

	def link_returned_secondary_items(self, original_rows):
		"""Link each rebuilt secondary row of a return to its row on the returned receipt."""
		if not original_rows:
			return

		secondary_rows = {}
		legacy_rows = defaultdict(list)
		for row in original_rows.values():
			if row.bom_secondary_item:
				secondary_rows[(row.reference_name, row.bom_secondary_item)] = row.name
			elif row.secondary_item_type or row.valuation_type:
				legacy_rows[row.reference_name].append(row)

		for fg_row in self.items:
			if fg_row.bom and fg_row.subcontracting_receipt_item in legacy_rows:
				secondary_rows.update(
					self.pair_legacy_secondary_rows(fg_row, legacy_rows[fg_row.subcontracting_receipt_item])
				)

		returned_fg_rows = {row.name: row.subcontracting_receipt_item for row in self.items if row.bom}
		for row in self.items:
			if row.bom_secondary_item:
				row.subcontracting_receipt_item = secondary_rows.get(
					(returned_fg_rows.get(row.reference_name), row.bom_secondary_item)
				)

	@staticmethod
	def pair_legacy_secondary_rows(fg_row, receipt_rows):
		"""Pair receipt rows made before v16 with the BOM rows of their item by qty rank, as migration may reorder the BOM."""
		bom_rows = frappe.get_cached_doc("BOM", fg_row.bom).secondary_items
		pairs = {}
		for item_code in {row.item_code for row in receipt_rows}:
			by_qty = sorted(
				(row for row in receipt_rows if row.item_code == item_code), key=lambda row: row.qty
			)
			bom_by_qty = sorted(
				(row for row in bom_rows if row.item_code == item_code), key=lambda row: row.stock_qty
			)
			for receipt_row, bom_row in zip(by_qty, bom_by_qty, strict=False):
				pairs[(fg_row.subcontracting_receipt_item, bom_row.name)] = receipt_row.name

		return pairs

	def set_remaining_secondary_qty(self, original_rows):
		"""A return of a receipt row's last finished goods takes the secondary qty left on it,
		so rounding leaves nothing behind."""
		last_fg_rows = [
			row.name for row in self.items if self.returns_last_finished_goods(row, original_rows)
		]
		if not last_fg_rows:
			return

		already_returned = get_already_returned_items(self)
		for row in self.items:
			if not (row.subcontracting_receipt_item and row.reference_name in last_fg_rows):
				continue

			original_row = original_rows[row.subcontracting_receipt_item]
			returned = already_returned.get((row.item_code, row.subcontracting_receipt_item), {})
			row.received_qty = flt(
				flt(returned.get("received_qty")) - original_row.received_qty, row.precision("received_qty")
			)
			row.qty = flt(flt(returned.get("qty")) - original_row.qty, row.precision("qty"))
			row.process_loss_qty = flt(row.received_qty - row.qty, row.precision("process_loss_qty"))

	def remove_returned_secondary_rows_without_qty(self):
		"""A return's secondary row that rounds to nothing is returned by a later return."""
		if not self.is_return:
			return

		for row in list(self.items):
			qty = flt(flt(row.received_qty) - flt(row.process_loss_qty), row.precision("qty"))
			if row.bom_secondary_item and not qty:
				self.remove(row)

	@staticmethod
	def returns_last_finished_goods(row, original_rows):
		original_row = original_rows.get(row.subcontracting_receipt_item)
		if not (row.bom and original_row):
			return False

		precision = row.precision("received_qty")
		return flt(original_row.returned_qty - flt(row.received_qty), precision) >= flt(
			original_row.received_qty - original_row.process_loss_qty, precision
		)

	def calculate_percentage_secondary_rows(self, percentage_rows, secondary_items_cost_map) -> dict:
		"""Price the % rows; returns the % allocated to them, by finished good row."""
		allocated_per = defaultdict(float)
		allocation_map = self.get_cost_allocation_map(percentage_rows)
		fg_rows = {row.name: row for row in self.get("items") if row.bom}
		for item in percentage_rows:
			qty = flt(item.received_qty) - flt(item.process_loss_qty)
			fg_row = fg_rows.get(item.reference_name)
			if qty and fg_row and item.bom_secondary_item in allocation_map:
				allocated_per[fg_row.name] += flt(allocation_map[item.bom_secondary_item])
				item.rate = self.get_percentage_secondary_rate(
					fg_row,
					flt(allocation_map[item.bom_secondary_item]),
					qty,
					secondary_items_cost_map.get(item.reference_name, 0),
				)
			item.amount = qty * flt(item.rate)

		return allocated_per

	def get_returned_allocated_per(self) -> dict:
		"""% allocated to the secondary rows of the returned receipt, by finished good row of the return."""
		original_rows = [
			row
			for row in self.get_returned_receipt_rows().values()
			if flt(row.qty) and row.valuation_type not in ("Valuation Rate", "Manual")
		]
		allocation_map = self.get_cost_allocation_map(original_rows)
		allocated_per = defaultdict(float)
		for row in original_rows:
			allocated_per[row.reference_name] += flt(allocation_map.get(row.bom_secondary_item))

		return {item.name: allocated_per[item.subcontracting_receipt_item] for item in self.items if item.bom}

	@staticmethod
	def get_cost_allocation_map(rows) -> dict:
		"""Cost Allocation % of each BOM secondary row the rows come from."""
		names = [row.bom_secondary_item for row in rows if row.bom_secondary_item]
		if not names:
			return {}

		return dict(
			frappe.get_all(
				"BOM Secondary Item",
				filters={"name": ("in", names)},
				fields=["name", "cost_allocation_per"],
				as_list=True,
			)
		)

	def get_secondary_item_valuation_rate(self, item):
		"""Valuation at the row's warehouse; keeps the stored rate when none is found."""
		return (
			self.get_valuation_rate_at_posting(item.item_code, item.warehouse or self.set_warehouse)
			or item.rate
		)

	def get_valuation_rate_at_posting(self, item_code, warehouse):
		return get_valuation_rate(
			item_code,
			warehouse,
			self.doctype,
			self.name,
			currency=erpnext.get_company_currency(self.company),
			company=self.company,
			posting_datetime=get_combine_datetime(self.posting_date, self.posting_time),
			creation=self.first_sle_creation,
		)

	def add_secondary_items_of_fg_row(self, item, fg_qty_before=0.0):
		"""Own-cost rows first: the percentage rows allocate from the cost net of them."""
		bom = frappe.get_doc("BOM", item.bom)
		warehouse = self.set_warehouse or item.warehouse

		own_cost = 0.0
		percentage_rows = []
		for secondary_item in bom.secondary_items:
			if secondary_item.valuation_type in ("Valuation Rate", "Manual"):
				row = self.append_secondary_item(item, bom, secondary_item, warehouse, 0.0, fg_qty_before)
				own_cost += flt(row.qty) * flt(row.rate)
			else:
				percentage_rows.append(secondary_item)

		for secondary_item in percentage_rows:
			self.append_secondary_item(item, bom, secondary_item, warehouse, own_cost, fg_qty_before)

	def append_secondary_item(self, item, bom, secondary_item, warehouse, own_cost=0.0, fg_qty_before=0.0):
		per_unit = secondary_item.stock_qty / bom.quantity
		received_qty = self.get_secondary_qty(item, per_unit, fg_qty_before, "received_qty")
		qty = self.get_secondary_qty(
			item, per_unit - (secondary_item.process_loss_qty / bom.quantity), fg_qty_before, "qty"
		)
		# a return's zero row is dropped, or priced from the receipt once it gets the qty left
		rate = (
			0.0
			if self.is_return and not qty
			else self.get_secondary_item_rate(item, secondary_item, warehouse, qty, own_cost)
		)

		return self.append(
			"items",
			{
				"secondary_item_type": secondary_item.secondary_item_type,
				"valuation_type": secondary_item.valuation_type,
				"bom_secondary_item": secondary_item.name,
				"reference_name": item.name,
				"item_code": secondary_item.item_code,
				"item_name": secondary_item.item_name,
				"qty": received_qty
				if secondary_item.valuation_type not in ("Valuation Rate", "Manual")
				else flt(item.qty) * (flt(secondary_item.stock_qty) / flt(bom.quantity)),
				"received_qty": received_qty,
				"process_loss_qty": received_qty - qty,
				"stock_uom": secondary_item.stock_uom,
				"conversion_factor": 1,
				"rate": rate,
				"rm_cost_per_qty": 0,
				"service_cost_per_qty": 0,
				"additional_cost_per_qty": 0,
				"secondary_items_cost_per_qty": 0,
				"amount": qty * rate,
				"warehouse": warehouse,
				"rejected_warehouse": self.rejected_warehouse,
			},
		)

	@staticmethod
	def get_secondary_qty(item, per_unit, fg_qty_before, fieldname):
		"""Rounded on the running finished good total, so a receipt's returns add up to its secondary qty."""
		precision = item.precision(fieldname)
		fg_qty_after = fg_qty_before + flt(item.received_qty)
		return flt(
			flt(fg_qty_after * per_unit, precision) - flt(fg_qty_before * per_unit, precision), precision
		)

	def get_secondary_item_rate(self, item, secondary_item, warehouse, qty, own_cost):
		if secondary_item.valuation_type == "Manual":
			if not flt(secondary_item.stock_qty):
				return 0
			return flt(secondary_item.base_cost) / flt(secondary_item.stock_qty)

		if secondary_item.valuation_type == "Valuation Rate":
			rate = self.get_valuation_rate_at_posting(secondary_item.item_code, warehouse)
			# the BOM costs the row on its qty net of process loss
			produced_qty = flt(secondary_item.stock_qty) - flt(secondary_item.process_loss_qty)
			if not rate and produced_qty:
				rate = flt(secondary_item.base_cost) / produced_qty
			return rate

		return self.get_percentage_secondary_rate(item, secondary_item.cost_allocation_per, qty, own_cost)

	def get_percentage_secondary_rate(self, fg_row, cost_allocation_per, qty, own_cost):
		received_qty = flt(fg_row.received_qty) or flt(fg_row.qty)
		lcv_cost_per_qty = flt(fg_row.landed_cost_voucher_amount) / received_qty if received_qty else 0.0
		fg_item_cost = (
			flt(fg_row.rm_cost_per_qty)
			+ flt(fg_row.additional_cost_per_qty)
			+ flt(lcv_cost_per_qty)
			+ flt(fg_row.service_cost_per_qty)
		) * flt(fg_row.received_qty) - flt(own_cost)
		return (fg_item_cost * (cost_allocation_per / 100)) / qty if qty else 0.0

	def remove_secondary_items(self):
		for item in list(self.items):
			if item.secondary_item_type or item.valuation_type:
				self.remove(item)
			else:
				item.secondary_items_cost_per_qty = 0

	@frappe.whitelist()
	def set_missing_values(self):
		self.set_available_qty_for_consumption()
		self.set_additional_costs_and_amounts()

	def set_additional_costs_and_amounts(self):
		if self.distribute_additional_costs_based_on == "Amount" and self.get("additional_costs"):
			# split on the amounts at the current qty and secondary rows
			self.calculate_items_qty_and_amount()
		self.set_additional_costs()
		self.calculate_items_qty_and_amount()

	def set_additional_costs(self):
		if self.is_return and self.return_against:
			self.set_additional_costs_for_return()
		else:
			self.set_work_order_costs()
			self.set_order_additional_costs()
			self.set_additional_costs_base_amount()
			self.calculate_additional_costs()

	def set_work_order_costs(self):
		"""Book the costs of a Work Order on the finished goods of its subcontracted final operation."""
		# the rows are rebuilt on every save, so keep the account a user picked;
		# item rows are renamed on first insert, so match by row order then
		by_order = self.is_new()
		accounts = defaultdict(list)
		for row in self.get("additional_costs"):
			if row.work_order:
				key = (row.work_order, None if by_order else row.item_row, cint(row.has_corrective_cost))
				accounts[key].append(row.expense_account)

		self.set("additional_costs", [row for row in self.get("additional_costs") if not row.work_order])
		qty_by_work_order = self.get_final_operation_qty()
		work_orders = self.get_final_operation_work_orders(list(qty_by_work_order))
		for work_order_name, qty_by_item_row in qty_by_work_order.items():
			for row in get_subcontracted_work_order_costs(work_orders[work_order_name], qty_by_item_row):
				item_row = None if by_order else row["item_row"]
				picked = accounts[(row["work_order"], item_row, cint(row.get("has_corrective_cost")))]
				row["expense_account"] = (picked.pop(0) if picked else None) or row["expense_account"]
				self.append("additional_costs", row)

	def get_final_operation_work_orders(self, names: list[str]) -> dict:
		"""Work Orders by name, with the fields their costs are worked out from."""
		if not names:
			return {}

		work_orders = frappe.get_all(
			"Work Order",
			filters={"name": ("in", names)},
			fields=[
				"name",
				"company",
				"qty",
				"production_item",
				"additional_operating_cost",
				"corrective_operation_cost",
			],
		)
		return {work_order.name: work_order for work_order in work_orders}

	def get_final_operation_qty(self) -> dict[str, dict[str, float]]:
		"""Accepted and process loss qty of each item row, by the Work Order whose final operation its job card is."""
		rows = [
			row
			for row in self.items
			if row.job_card and row.name and flt(row.qty) + flt(row.process_loss_qty) > 0
		]
		if not rows:
			return {}

		job_cards = frappe.get_all(
			"Job Card",
			filters={"name": ("in", list({row.job_card for row in rows}))},
			fields=["name", "work_order", "finished_good", "production_item"],
		)
		work_orders = {
			job_card.name: job_card.work_order
			for job_card in job_cards
			if job_card.work_order and job_card.finished_good == job_card.production_item
		}

		qty = defaultdict(dict)
		for row in rows:
			if work_order := work_orders.get(row.job_card):
				qty[work_order][row.name] = flt(row.qty) + flt(row.process_loss_qty)
		return qty

	def validate_order_costs_are_not_repeated(self):
		"""Each order cost row is recomputed in full, so it can be mapped only once."""
		seen = set()
		for row in self.get("additional_costs"):
			if not row.subcontracting_order_cost:
				continue
			if row.subcontracting_order_cost in seen:
				frappe.throw(
					_(
						"Row #{0}: This Additional Costs row repeats a cost of the Subcontracting Order. Remove it."
					).format(row.idx),
					title=_("Duplicate Additional Cost"),
				)
			seen.add(row.subcontracting_order_cost)

	def set_order_additional_costs(self):
		"""Give each cost row mapped from a Subcontracting Order its share of what the order's row has left."""
		rows = [row for row in self.get("additional_costs") if row.subcontracting_order_cost]
		if not rows:
			return

		costs_left = self.get_order_costs_left([row.subcontracting_order_cost for row in rows])
		shares = self.get_order_additional_cost_shares()
		for row in rows:
			order, cost_left = costs_left[row.subcontracting_order_cost]
			row.amount = flt(cost_left * shares.get(order, 0), row.precision("amount"))

	def get_order_costs_left(self, order_costs: list[str]) -> dict[str, tuple[str, float]]:
		"""Order and amount each order cost row has left after the submitted receipts."""
		charges = frappe.qb.DocType("Landed Cost Taxes and Charges")
		taken = dict(
			frappe.qb.from_(charges)
			.select(charges.subcontracting_order_cost, Sum(charges.amount))
			.where(
				(charges.parenttype == "Subcontracting Receipt")
				& (charges.docstatus == 1)
				& charges.subcontracting_order_cost.isin(order_costs)
			)
			.groupby(charges.subcontracting_order_cost)
			.run()
		)
		order = frappe.qb.DocType("Subcontracting Order")
		rows = (
			frappe.qb.from_(charges)
			.inner_join(order)
			.on(order.name == charges.parent)
			.select(charges.name, charges.parent, charges.amount, order.total_additional_costs)
			.where((charges.parenttype == "Subcontracting Order") & charges.name.isin(order_costs))
			.run(as_dict=True)
		)
		unlinked_taken = self.get_order_costs_taken_by_unlinked_receipts(list({row.parent for row in rows}))
		costs_left = {}
		for row in rows:
			# unlinked receipts take from each order row by its share of the order's cost
			row_share = (
				flt(row.amount) / flt(row.total_additional_costs) if flt(row.total_additional_costs) else 0
			)
			row_taken = flt(taken.get(row.name)) + flt(unlinked_taken.get(row.parent)) * row_share
			cost_left = flt(row.amount) - row_taken
			# a row booked in full or more before the upgrade has nothing left, never a reversal
			costs_left[row.name] = (row.parent, cost_left if cost_left * flt(row.amount) > 0 else 0)
		return costs_left

	def get_order_costs_taken_by_unlinked_receipts(self, orders: list[str]) -> dict[str, float]:
		"""Additional costs each order's submitted receipts booked without cost rows linked to the order."""
		receipt = frappe.qb.DocType("Subcontracting Receipt")
		receipt_item = frappe.qb.DocType("Subcontracting Receipt Item")
		charges = frappe.qb.DocType("Landed Cost Taxes and Charges")
		order_charges = frappe.qb.DocType("Landed Cost Taxes and Charges").as_("order_charges")
		# receipts with a cost row linked to this item row's order
		linked_receipts = (
			frappe.qb.from_(charges)
			.inner_join(order_charges)
			.on(order_charges.name == charges.subcontracting_order_cost)
			.select(charges.parent)
			.where(
				(charges.parenttype == "Subcontracting Receipt")
				& (order_charges.parent == receipt_item.subcontracting_order)
			)
		)
		unlinked = (
			(receipt.docstatus == 1)
			& receipt_item.subcontracting_order.isin(orders)
			& receipt.name.notin(linked_receipts)
		)
		costing_qty = receipt_item.qty + receipt_item.rejected_qty + receipt_item.process_loss_qty
		booked = (
			frappe.qb.from_(receipt_item)
			.inner_join(receipt)
			.on(receipt.name == receipt_item.parent)
			.select(
				receipt_item.subcontracting_order, Sum(costing_qty * receipt_item.additional_cost_per_qty)
			)
			.where(unlinked)
			.groupby(receipt_item.subcontracting_order)
			.run()
		)
		# costs a receipt gives to one item row, such as Work Order costs, are not the order's
		targeted_charges = frappe.qb.DocType("Landed Cost Taxes and Charges").as_("targeted_charges")
		targeted = dict(
			frappe.qb.from_(targeted_charges)
			.inner_join(receipt_item)
			.on(receipt_item.name == targeted_charges.item_row)
			.inner_join(receipt)
			.on(receipt.name == targeted_charges.parent)
			.select(receipt_item.subcontracting_order, Sum(targeted_charges.base_amount))
			.where(unlinked & (targeted_charges.parenttype == "Subcontracting Receipt"))
			.groupby(receipt_item.subcontracting_order)
			.run()
		)
		return {order: flt(cost) - flt(targeted.get(order)) for order, cost in booked}

	def get_order_additional_cost_shares(self) -> dict[str, float]:
		"""Share of each order's pending additional costs that this receipt's qty takes."""
		received_qty = defaultdict(float)
		for row in self.items:
			if row.subcontracting_order_item:
				received_qty[row.subcontracting_order_item] += self.get_qty_for_costing(row)

		orders = list({row.subcontracting_order for row in self.items if row.subcontracting_order})
		order_items = frappe.get_all(
			"Subcontracting Order Item",
			filters={"parent": ("in", orders)},
			fields=["name", "parent", "qty", "received_qty", "additional_cost_per_qty"],
		)
		# orders whose costs net to zero are shared by qty
		costed_orders = {row.parent for row in order_items if flt(row.additional_cost_per_qty)}
		pending, received = defaultdict(float), defaultdict(float)
		for row in order_items:
			weight = flt(row.additional_cost_per_qty) if row.parent in costed_orders else 1
			pending[row.parent] += max(flt(row.qty) - flt(row.received_qty), 0) * weight
			received[row.parent] += received_qty[row.name] * weight

		return {order: min(received[order] / pending[order], 1) if pending[order] else 0 for order in pending}

	def set_additional_costs_for_return(self):
		"""Take back the original receipt's additional costs allocated to the accepted qty returned."""
		original = frappe.get_doc("Subcontracting Receipt", self.return_against, check_permission="read")
		original_rows = {row.name: row for row in original.items if row.bom}
		based_on_amount = original.distribute_additional_costs_based_on == "Amount"
		basis = {
			name: self.get_amount_for_costing(row) if based_on_amount else self.get_qty_for_costing(row)
			for name, row in original_rows.items()
		}
		total_basis = sum(basis.values())
		total_cost = sum(
			self.get_qty_for_costing(row) * flt(row.additional_cost_per_qty) for row in original_rows.values()
		)
		returned_basis = returned_cost = 0.0
		returned_ratios = defaultdict(float)
		for row in self.items:
			original_row = original_rows.get(row.subcontracting_receipt_item)
			if not original_row:
				continue

			row.additional_cost_per_qty = 0.0
			if flt(original_row.qty) and row.warehouse and row.warehouse != original_row.rejected_warehouse:
				row_returned_cost = (
					flt(row.qty)
					* flt(original_row.additional_cost_per_qty)
					* self.get_qty_for_costing(original_row)
					/ flt(original_row.qty)
				)
				costing_qty = self.get_qty_for_costing(row)
				row.additional_cost_per_qty = row_returned_cost / costing_qty if costing_qty else 0.0
				returned_cost += row_returned_cost
				returned_basis += flt(row.qty) * basis[original_row.name] / flt(original_row.qty)
				returned_ratios[original_row.name] += flt(row.qty) / flt(original_row.qty)

		# a targeted row is taken back with its item row, the others share what is left
		targeted_rows = [row for row in original.additional_costs if row.item_row]
		returned_orders = {original_rows[name].subcontracting_order for name in returned_ratios}
		kept_rows = self.get_order_costs_kept_by_return(original, returned_orders)
		untargeted_cost = flt(
			total_cost - sum(flt(row.amount) for row in targeted_rows + kept_rows),
			self.precision("total_additional_costs"),
		)
		if untargeted_cost:
			targeted_returned = sum(flt(row.amount) * returned_ratios[row.item_row] for row in targeted_rows)
			ratio = (returned_cost - targeted_returned) / untargeted_cost
		else:
			ratio = returned_basis / total_basis if total_basis else 0.0

		self.set("additional_costs", [])
		for row in original.additional_costs:
			row_ratio = returned_ratios[row.item_row] if row.item_row else ratio
			if row in kept_rows:
				row_ratio = 0.0
			self.append(
				"additional_costs",
				{
					"expense_account": row.expense_account,
					"account_currency": row.account_currency,
					"exchange_rate": row.exchange_rate,
					"description": row.description,
					"has_corrective_cost": row.has_corrective_cost,
					"work_order": row.work_order,
					"item_row": row.item_row,
					"subcontracting_order_cost": row.subcontracting_order_cost,
					"amount": flt(row.amount * row_ratio, row.precision("amount")),
					"base_amount": flt(row.base_amount * row_ratio, row.precision("base_amount")),
				},
			)
		self.total_additional_costs = sum(flt(row.amount) for row in self.additional_costs)

	def get_order_costs_kept_by_return(self, original: Document, returned_orders: set[str]) -> list:
		"""Original cost rows of orders none of whose goods are returned; no later receipt books them again."""
		linked_rows = [
			row for row in original.additional_costs if row.subcontracting_order_cost and not row.item_row
		]
		if not linked_rows:
			return []

		order_of_cost = dict(
			frappe.get_all(
				"Landed Cost Taxes and Charges",
				filters={"name": ("in", [row.subcontracting_order_cost for row in linked_rows])},
				fields=["name", "parent"],
				as_list=True,
			)
		)
		kept_rows = [
			row
			for row in linked_rows
			if order_of_cost.get(row.subcontracting_order_cost) not in returned_orders
		]
		# keep them only if other rows are left to take back the returned cost
		shared_cost = sum(
			flt(row.amount) for row in original.additional_costs if not row.item_row and row not in kept_rows
		)
		return kept_rows if flt(shared_cost, self.precision("total_additional_costs")) else []

	def get_amount_for_costing(self, item):
		"""Row amount without the additional costs it took last time, so a re-save keeps the same weights."""
		# the amount holds only the finished good's allocated share of its cost
		allocation = flt(frappe.get_value("BOM", item.bom, "cost_allocation_per")) / 100 if item.bom else 1
		additional_cost = self.get_qty_for_costing(item) * flt(item.additional_cost_per_qty) * allocation
		return flt(item.amount) - additional_cost

	def set_additional_costs_base_amount(self):
		for row in self.get("additional_costs"):
			row.base_amount = flt(
				flt(row.amount) * (flt(row.exchange_rate) or 1), row.precision("base_amount")
			)

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

		# before the percentage rows, which are priced from it
		for item in self.get("items") or []:
			if item.qty and item.name in rm_cost_map:
				item.rm_supp_cost = rm_cost_map[item.name]
				item.rm_cost_per_qty = item.rm_supp_cost / (item.received_qty or item.qty)

		# own-cost rows first: they are deducted from the finished good, and the
		# percentage rows reprice from the basis net of them
		secondary_items_cost_map = {}
		percentage_rows = []
		is_return = self.is_return and self.return_against
		for item in self.get("items") or []:
			if not (item.secondary_item_type or item.valuation_type):
				continue

			if is_return:
				# the stock ledger returns the secondary item at its receipt rate
				item.rate = get_rate_for_return(
					self.doctype, self.name, item.item_code, self.return_against, item_row=item
				)
			elif item.valuation_type == "Valuation Rate":
				# Recomputed every time: a rate fetched against another warehouse
				# must not stick to the row when the warehouse changes.
				item.rate = self.get_secondary_item_valuation_rate(item)

			if item.valuation_type in ("Valuation Rate", "Manual"):
				# net of process loss before it is deducted, as the rows below are
				item.qty = flt(item.received_qty) - flt(item.process_loss_qty)
				item.amount = flt(item.qty) * flt(item.rate)
				secondary_items_cost_map[item.reference_name] = (
					secondary_items_cost_map.get(item.reference_name, 0) + item.amount
				)
			elif not is_return:
				percentage_rows.append(item)

		# the stock ledger returns the finished good at its receipt rate, so a return takes the receipt's share
		allocated_per = (
			self.get_returned_allocated_per()
			if is_return
			else self.calculate_percentage_secondary_rows(percentage_rows, secondary_items_cost_map)
		)

		rejected_return_rows = self.get_rejected_return_rows()
		received_qty_ratios = self.get_received_qty_ratios_for_return(rejected_return_rows)
		returned_costs = self.get_returned_costs()
		total_qty = total_amount = 0
		for item in self.get("items") or []:
			if not item.secondary_item_type and not item.valuation_type:
				returned = returned_costs.get(item.name)
				# rejected qty is received without service cost
				if returned:
					item.service_cost_per_qty = (
						0.0 if item.name in rejected_return_rows else returned.service_cost_per_qty
					)

				if item.qty:
					# the stock ledger returns the finished good at its receipt rate
					if returned and item.name not in rejected_return_rows:
						item.secondary_items_cost_per_qty = returned.secondary_items_cost_per_qty
					elif item.name in secondary_items_cost_map:
						item.secondary_items_cost_per_qty = secondary_items_cost_map[item.name] / (
							item.received_qty or item.qty
						)
						secondary_items_cost_map.pop(item.name)
					else:
						item.secondary_items_cost_per_qty = 0

				lcv_cost_per_qty = 0.0
				if item.landed_cost_voucher_amount:
					lcv_cost_per_qty = item.landed_cost_voucher_amount / (item.received_qty or item.qty)

				item.rate = (
					flt(item.rm_cost_per_qty)
					+ flt(item.service_cost_per_qty)
					+ flt(item.additional_cost_per_qty)
					+ flt(lcv_cost_per_qty)
					- flt(item.secondary_items_cost_per_qty)
				)

			if item.bom:
				item.received_qty = self.get_qty_for_costing(item)
				if item.name in received_qty_ratios:
					additional_cost = flt(item.received_qty) * flt(item.additional_cost_per_qty)
					amount = (
						flt(item.qty)
						* received_qty_ratios[item.name]
						* (flt(item.rate) - flt(item.additional_cost_per_qty))
						+ additional_cost
					)
				else:
					amount = flt(item.received_qty) * flt(item.rate)
				item.amount = amount * (100 - allocated_per[item.name]) / 100
				item.rate = item.amount / (item.qty or item.rejected_qty)
			else:
				item.qty = flt(item.received_qty) - flt(item.process_loss_qty)
				item.amount = flt(item.qty) * flt(item.rate)

			total_qty += flt(item.qty) + flt(item.rejected_qty)
			total_amount += item.amount
		else:
			self.total_qty = total_qty
			self.total = total_amount

	def get_returned_costs(self) -> dict[str, frappe._dict]:
		"""Service and secondary items cost per qty of the returned receipt row, for each return row."""
		if not (self.is_return and self.return_against):
			return {}

		received_rows = {
			row.name: row
			for row in frappe.get_all(
				"Subcontracting Receipt Item",
				filters={"parent": self.return_against, "parenttype": "Subcontracting Receipt"},
				fields=["name", "service_cost_per_qty", "secondary_items_cost_per_qty"],
			)
		}
		return {
			item.name: received_rows[item.subcontracting_receipt_item]
			for item in self.items
			if item.subcontracting_receipt_item in received_rows
		}

	def get_received_qty_ratios_for_return(self, rejected_return_rows: set[str]) -> dict[str, float]:
		"""Received qty per accepted qty of the original row, for each return row of accepted qty."""
		if not (self.is_return and self.return_against):
			return {}

		original_rows = {
			row.name: row
			for row in frappe.get_all(
				"Subcontracting Receipt Item",
				filters={"parent": self.return_against, "parenttype": "Subcontracting Receipt"},
				fields=["name", "qty", "received_qty"],
			)
		}

		ratios = {}
		for item in self.items:
			original_row = original_rows.get(item.subcontracting_receipt_item)
			if original_row and flt(original_row.qty) and item.name not in rejected_return_rows:
				ratios[item.name] = flt(original_row.received_qty) / flt(original_row.qty)

		return ratios

	def validate_secondary_items(self):
		fg_rows = {item.name for item in self.items if not (item.secondary_item_type or item.valuation_type)}
		for item in self.items:
			if item.secondary_item_type or item.valuation_type:
				if not item.qty:
					frappe.throw(
						_("Row #{0}: Secondary Item Qty cannot be zero").format(item.idx),
					)

				if item.rejected_qty:
					frappe.throw(
						_("Row #{0}: Rejected Qty cannot be set for Secondary Item {1}.").format(
							item.idx, frappe.bold(item.item_code)
						),
					)

				if not item.reference_name:
					frappe.throw(
						_("Row #{0}: Finished Good reference is mandatory for Secondary Item {1}.").format(
							item.idx, frappe.bold(item.item_code)
						),
					)

				if item.reference_name not in fg_rows:
					frappe.throw(
						_(
							"Row #{0}: The Finished Good row of Secondary Item {1} is not on this receipt. Remove the Secondary Item row."
						).format(item.idx, frappe.bold(item.item_code)),
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

	def validate_bom_required_qty(self):
		# a return takes back what the receipt consumed, not what the BOM needs
		if self.is_return or (
			frappe.db.get_single_value("Buying Settings", "backflush_raw_materials_of_subcontract_based_on")
			== "Material Transferred for Subcontract"
			and not frappe.db.get_single_value("Buying Settings", "validate_consumed_qty")
		):
			return

		precision = frappe.get_precision("Subcontracting Receipt Item", "qty")
		rm_consumed_dict = self.get_rm_wise_consumed_qty()

		for rm_item_code, required in self.get_rm_wise_required_qty(precision).items():
			diff = flt(rm_consumed_dict.get(rm_item_code, 0) - required.qty, precision)

			if diff < 0:
				msg = _(
					"""Additional {0} {1} of item {2} required as per BOM to complete this transaction"""
				).format(
					frappe.bold(abs(diff)),
					frappe.bold(required.stock_uom),
					frappe.bold(rm_item_code),
				)

				frappe.throw(
					msg,
					exc=BOMQuantityError,
				)

	def get_rm_wise_required_qty(self, precision: int) -> dict:
		rm_dict = {}

		for row in self.items:
			if frappe.db.get_value("BOM", row.bom, "allow_alternative_item"):
				continue

			for bom_item in self._get_materials_from_bom(
				row.item_code, row.bom, row.get("include_exploded_items")
			):
				required = rm_dict.setdefault(
					bom_item.rm_item_code, frappe._dict(qty=0.0, stock_uom=bom_item.stock_uom)
				)
				required.qty += flt(
					bom_item.qty_consumed_per_unit * self.get_qty_for_costing(row) * row.conversion_factor,
					precision,
				)

		return rm_dict

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
						# a return sends back no process loss
						"target_ref_field": {
							"SUB": ["received_qty", "process_loss_qty"],
							"as": "returnable_qty",
						},
						"source_field": "-1 * received_qty",
						"percent_join_field_parent": "return_against",
						# validate_return checks over-returns
						"validate_qty": False,
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

		remarks = self.get("remarks") or _("Accounting Entry for Stock")
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

		received_qty_ratios = self.get_received_qty_ratios_for_return(self.get_rejected_return_rows())
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

					# the stock value holds the service cost of rejected and lost units too
					if item.name in received_qty_ratios:
						service_qty = flt(item.qty) * received_qty_ratios[item.name]
					else:
						service_qty = self.get_qty_for_costing(item)

					service_cost = flt(flt(item.service_cost_per_qty) * service_qty, item.precision("amount"))
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

					if divisional_loss := flt(item.amount - stock_value_diff, item.precision("amount")):
						loss_account = self.get_company_default(
							"stock_adjustment_account", ignore_validation=True
						)

						# the receipt amount the ledger did not take into stock is a loss
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=loss_account,
							cost_center=item.cost_center,
							debit=divisional_loss,
							credit=0.0,
							remarks=remarks,
							against_account=item.expense_account,
							account_currency=get_account_currency(loss_account),
							project=item.project,
							item=item,
						)
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=item.expense_account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=divisional_loss,
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

			self._make_supplied_items_gl_entries(
				gl_entries, item, supplied_items_details.get(item.name, []), inventory_account_map, remarks
			)

			if item.additional_cost_per_qty:
				self.add_gl_entry(
					gl_entries=gl_entries,
					account=item.expense_account,
					cost_center=self.cost_center or self.get_company_default("cost_center"),
					debit=flt(item.received_qty) * item.additional_cost_per_qty,
					credit=0.0,
					remarks=remarks,
					against_account=None,
					account_currency=get_account_currency(item.expense_account),
				)

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

	def _make_supplied_items_gl_entries(
		self, gl_entries: list, item, supplied_items: list, inventory_account_map: dict | None, remarks: str
	) -> None:
		"""Credit the supplier warehouse for consumed raw materials, also when the row has no accepted qty."""
		for rm_item in supplied_items:
			if not flt(rm_item.amount):
				continue

			_inv_dict = self.get_inventory_account_dict(rm_item, inventory_account_map, "supplier_warehouse")
			expense_account = rm_item.expense_account or item.expense_account

			self.add_gl_entry(
				gl_entries=gl_entries,
				account=_inv_dict.get("account"),
				cost_center=rm_item.cost_center or item.cost_center,
				debit=0.0,
				credit=flt(rm_item.amount),
				remarks=remarks,
				against_account=expense_account,
				account_currency=_inv_dict.get("account_currency"),
				project=item.project,
				item=item,
			)
			self.add_gl_entry(
				gl_entries=gl_entries,
				account=expense_account,
				cost_center=rm_item.cost_center or item.cost_center,
				debit=flt(rm_item.amount),
				credit=0.0,
				remarks=remarks,
				against_account=_inv_dict.get("account"),
				account_currency=get_account_currency(item.expense_account),
				project=item.project,
				item=item,
			)

	def make_item_gl_entries_for_lcv(self, gl_entries, inventory_account_map):
		from erpnext.stock.doctype.landed_cost_voucher.landed_cost_voucher import (
			get_custom_dimension_overrides,
		)

		landed_cost_entries = self.get_item_account_wise_lcv_entries()

		if not landed_cost_entries:
			return

		for item in self.items:
			item_entries = landed_cost_entries.get((item.item_code, item.name), [])

			if item.landed_cost_voucher_amount and item_entries:
				remarks = _("Accounting Entry for Landed Cost Voucher for SCR {0}").format(self.name)
				_inv_dict = self.get_inventory_account_dict(item, inventory_account_map)

				for entry in item_entries:
					if not (entry.amount or entry.base_amount):
						continue

					account_currency = get_account_currency(entry.expense_account)
					credit_amount = (
						flt(entry.base_amount)
						if (entry.base_amount or account_currency != self.company_currency)
						else flt(entry.amount)
					)

					self.add_gl_entry(
						gl_entries=gl_entries,
						account=entry.expense_account,
						cost_center=entry.dimensions.cost_center or item.cost_center,
						debit=0.0,
						credit=credit_amount,
						remarks=remarks,
						against_account=_inv_dict["account"],
						credit_in_account_currency=flt(entry.amount),
						account_currency=account_currency,
						project=entry.dimensions.project or item.project,
						item=item,
						dimensions=get_custom_dimension_overrides(entry),
					)

					account_currency = get_account_currency(item.expense_account)

					self.add_gl_entry(
						gl_entries=gl_entries,
						account=item.expense_account,
						cost_center=item.cost_center,
						debit=0.0,
						credit=credit_amount * -1,
						remarks=remarks,
						against_account=_inv_dict["account"],
						debit_in_account_currency=flt(entry.amount),
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


@frappe.whitelist(methods=["POST"])
def make_purchase_receipt(
	source_name: Document | str,
	target_doc: str | dict | Document | None = None,
	save: bool = False,
	submit: bool = False,
	notify: bool = False,
):
	if isinstance(source_name, str):
		source_doc = frappe.get_doc("Subcontracting Receipt", source_name)
	else:
		source_doc = source_name

	if source_doc.is_return:
		return

	validate_no_purchase_receipt_made(source_doc)

	po_sr_items = defaultdict(list)
	for item in source_doc.items:
		if item.purchase_order:
			po_sr_items[item.purchase_order_item].append(item)

	purchase_orders = get_purchase_orders(source_doc)
	if not purchase_orders:
		frappe.throw(
			_("Purchase Order Item reference is missing in Subcontracting Receipt {0}").format(
				source_doc.name
			)
		)

	if not can_combine_purchase_orders(purchase_orders):
		frappe.throw(get_uncombinable_orders_message(purchase_orders), title=_("Cannot Combine Orders"))

	def update_item(obj, target, source_parent):
		sr_items = po_sr_items[obj.name]
		ratio = flt(obj.qty) / flt(obj.fg_item_qty)

		target.update(
			{
				# the job worker did the work on the units lost in process too
				"qty": ratio * sum(flt(item.qty) + flt(item.process_loss_qty) for item in sr_items),
				"rejected_qty": ratio * sum(flt(item.rejected_qty) for item in sr_items),
				"warehouse": sr_items[0].warehouse,
				"rejected_warehouse": next(
					(item.rejected_warehouse for item in sr_items if item.rejected_warehouse), None
				),
				"subcontracting_receipt_item": sr_items[0].name,
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
			}
		)

	target_doc = None
	first_order_charges = 0
	for po_name in purchase_orders:
		is_first_order = target_doc is None
		charges_before = len(target_doc.taxes) if target_doc else 0
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
					"condition": lambda doc: doc.name in po_sr_items,
				},
				"Purchase Taxes and Charges": {
					"doctype": "Purchase Taxes and Charges",
					"reset_value": is_first_order,
					# for POs created in earlier version with tax_withholding_row
					"condition": lambda doc: (
						not doc.is_tax_withholding_account and (is_first_order or doc.charge_type == "Actual")
					),
				},
			},
			target_doc,
			postprocess=post_process,
		)
		if is_first_order:
			first_order_charges = len(target_doc.taxes)
		else:
			merge_order_charges(target_doc, first_order_charges, charges_before)

	target_doc.calculate_taxes_and_totals()

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


def merge_order_charges(target_doc, first_order_charges: int, order_charges_start: int):
	"""Fold an order's Actual charges into the first order's rows, matching repeated charges by position."""
	key_fields = get_charge_key_fields()

	def get_charge_key(row) -> tuple:
		return tuple(row.get(field) for field in key_fields)

	first_order_rows = defaultdict(list)
	for row in target_doc.taxes[:first_order_charges]:
		if row.charge_type == "Actual":
			first_order_rows[get_charge_key(row)].append(row)

	for row in target_doc.taxes[order_charges_start:]:
		if matching_rows := first_order_rows.get(get_charge_key(row)):
			first_row = matching_rows.pop(0)
			first_row.tax_amount = flt(first_row.tax_amount) + flt(row.tax_amount)
			target_doc.remove(row)

	for idx, row in enumerate(target_doc.taxes, 1):
		row.idx = idx


def validate_no_purchase_receipt_made(scr_doc):
	if scr_doc.docstatus != 1:
		frappe.throw(
			_("Submit Subcontracting Receipt {0} before making a Purchase Receipt").format(scr_doc.name)
		)

	validate_single_purchase_receipt(scr_doc.name)


def validate_single_purchase_receipt(subcontracting_receipt, purchase_receipt=None):
	if existing := frappe.db.get_value(
		"Purchase Receipt",
		{
			"subcontracting_receipt": subcontracting_receipt,
			"is_return": 0,
			"docstatus": ("<", 2),
			"name": ("!=", purchase_receipt or ""),
		},
	):
		frappe.throw(
			_("Purchase Receipt {0} is already made against Subcontracting Receipt {1}").format(
				get_link_to_form("Purchase Receipt", existing), subcontracting_receipt
			)
		)


def get_purchase_orders(scr_doc) -> list[str]:
	return list(dict.fromkeys(item.purchase_order for item in scr_doc.items if item.purchase_order))


def can_combine_purchase_orders(purchase_orders: list[str]) -> bool:
	"""One Purchase Receipt carries one currency, one set of rate-based taxes and one header discount."""
	return len(purchase_orders) < 2 or len(get_purchase_order_terms(purchase_orders)) == 1


def get_purchase_order_terms(purchase_orders: list[str]) -> set[tuple]:
	key_fields = get_charge_key_fields()
	taxes = get_purchase_order_taxes(purchase_orders, key_fields)
	return {
		(order.currency, get_tax_terms(taxes[order.name], key_fields), get_discount_terms(order))
		for order in frappe.get_all(
			"Purchase Order",
			filters={"name": ["in", purchase_orders]},
			fields=[
				"name",
				"currency",
				"apply_discount_on",
				"additional_discount_percentage",
				"discount_amount",
			],
		)
	}


def get_purchase_order_taxes(purchase_orders: list[str], key_fields: list[str]) -> dict[str, list]:
	taxes = defaultdict(list)
	for row in frappe.get_all(
		"Purchase Taxes and Charges",
		filters={
			"parenttype": "Purchase Order",
			"parent": ["in", purchase_orders],
			"is_tax_withholding_account": 0,
		},
		fields=["parent", "charge_type", "row_id", "rate", "included_in_print_rate", *key_fields],
		order_by="idx",
	):
		taxes[row.parent].append(row)

	return taxes


def get_discount_terms(order) -> tuple:
	"""A percentage discount can be shared by orders; an amount discount belongs to its order alone."""
	if flt(order.additional_discount_percentage):
		return (order.apply_discount_on, flt(order.additional_discount_percentage))
	if flt(order.discount_amount):
		return (order.name,)
	return ()


def get_tax_terms(taxes: list, key_fields: list[str]) -> tuple:
	"""Rate-based taxes, plus the Actual charges when a tax is calculated on a previous row."""
	has_row_based_tax = any(row.charge_type in ROW_BASED_CHARGE_TYPES for row in taxes)

	return tuple(
		(
			row.charge_type,
			row.row_id,
			flt(row.rate),
			row.included_in_print_rate,
			*(row.get(field) for field in key_fields),
		)
		for row in taxes
		if has_row_based_tax or row.charge_type != "Actual"
	)


def get_charge_key_fields() -> list[str]:
	return [
		"account_head",
		"category",
		"add_deduct_tax",
		"cost_center",
		"project",
		*get_accounting_dimensions(),
	]


def get_uncombinable_orders_message(purchase_orders: list[str]) -> str:
	return _(
		"Purchase Orders {0} have different currencies, taxes or discounts, so they cannot share one Purchase Receipt. Make one Subcontracting Receipt for each Purchase Order."
	).format(comma_and([get_link_to_form("Purchase Order", name) for name in purchase_orders]))


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
						"project": item.project,
						"cost_center": item.cost_center,
					},
				)
