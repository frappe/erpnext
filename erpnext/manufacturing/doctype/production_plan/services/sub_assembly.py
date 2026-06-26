# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Sub-assembly item resolution for a Production Plan (extracted from production_plan.py)."""

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.manufacturing.doctype.production_plan.services.sub_assembly_queries import (
	get_sub_assembly_items,
)


class SubAssemblyService:
	def __init__(self, doc):
		self.doc = doc

	def get_sub_assembly_items(self, manufacturing_type: str | None = None):
		"Fetch sub assembly items and optionally combine them."
		self.doc.sub_assembly_items = []
		sub_assembly_items_store = []  # temporary store to process all subassembly items
		bin_details = frappe._dict()

		processed_any = False
		for row in self.doc.po_items:
			if self._collect_row_sub_assembly_items(
				row, sub_assembly_items_store, bin_details, manufacturing_type
			):
				processed_any = True

		if processed_any and not sub_assembly_items_store and self.doc.skip_available_sub_assembly_item:
			self._warn_sufficient_sub_assembly()

		if self.doc.combine_sub_items:
			sub_assembly_items_store = self.combine_subassembly_items(sub_assembly_items_store)

		for idx, row in enumerate(sub_assembly_items_store):
			row.idx = idx + 1
			self.doc.append("sub_assembly_items", row)

		self.set_default_supplier_for_subcontracting_order()

	def _collect_row_sub_assembly_items(self, row, sub_assembly_items_store, bin_details, manufacturing_type):
		self._validate_sub_assembly_row(row)
		if self._bom_tracks_semi_finished(row):
			return False

		bom_data = []
		get_sub_assembly_items(
			[item.production_item for item in sub_assembly_items_store],
			bin_details,
			row.bom_no,
			bom_data,
			row.planned_qty,
			self.doc.company,
			warehouse=self.doc.sub_assembly_warehouse,
			skip_available_sub_assembly_item=self.doc.skip_available_sub_assembly_item,
		)
		self.set_sub_assembly_items_based_on_level(row, bom_data, manufacturing_type)
		sub_assembly_items_store.extend(bom_data)
		return True

	@staticmethod
	def _bom_tracks_semi_finished(row):
		if not frappe.db.get_value("BOM", row.bom_no, "track_semi_finished_goods"):
			return False

		frappe.msgprint(
			_(
				"Row #{0}: Since 'Track Semi Finished Goods' is enabled, the BOM {1} cannot be used for Sub Assembly Items"
			).format(row.idx, row.bom_no)
		)
		return True

	def _validate_sub_assembly_row(self, row):
		if self.doc.skip_available_sub_assembly_item and not self.doc.sub_assembly_warehouse:
			frappe.throw(_("Row #{0}: Please select the Sub Assembly Warehouse").format(row.idx))
		if not row.item_code:
			frappe.throw(_("Row #{0}: Please select Item Code in Assembly Items").format(row.idx))
		if not row.bom_no:
			frappe.throw(_("Row #{0}: Please select the BOM No in Assembly Items").format(row.idx))

	def _warn_sufficient_sub_assembly(self):
		label = self.meta.get_field("skip_available_sub_assembly_item").label
		message = (
			_(
				"As there are sufficient Sub Assembly Items, Work Order is not required for Warehouse {0}."
			).format(self.doc.sub_assembly_warehouse)
			+ "<br><br>"
		)
		message += _("If you still want to proceed, please disable {0} checkbox.").format(label)
		frappe.msgprint(message, title=_("Note"))

	def set_sub_assembly_items_based_on_level(self, row, bom_data, manufacturing_type=None):
		"Modify bom_data, set additional details."
		is_group_warehouse = frappe.db.get_value("Warehouse", self.doc.sub_assembly_warehouse, "is_group")

		for data in bom_data:
			data.qty = data.stock_qty
			data.production_plan_item = row.name
			data.schedule_date = row.planned_start_date
			data.type_of_manufacturing = manufacturing_type or (
				"Subcontract" if data.is_sub_contracted_item else "In House"
			)

			if not is_group_warehouse:
				data.fg_warehouse = self.doc.sub_assembly_warehouse

			if not self.doc.combine_sub_items:
				data.sales_order = row.sales_order
				data.sales_order_item = row.sales_order_item

	def set_default_supplier_for_subcontracting_order(self):
		items = [
			d.production_item for d in self.doc.sub_assembly_items if d.type_of_manufacturing == "Subcontract"
		]
		if not items:
			return

		default_supplier = self._default_suppliers(items)
		if not default_supplier:
			return

		for row in self.doc.sub_assembly_items:
			if row.type_of_manufacturing == "Subcontract":
				row.supplier = default_supplier.get(row.production_item)

	@staticmethod
	def _default_suppliers(items):
		return frappe._dict(
			frappe.get_all(
				"Item Default",
				fields=["parent", "default_supplier"],
				filters={"parent": ("in", items), "default_supplier": ("is", "set")},
				as_list=1,
			)
		)

	def combine_subassembly_items(self, sub_assembly_items_store):
		"Aggregate if same: Item, Warehouse, Inhouse/Outhouse Manu.g, BOM No."
		key_wise_data = {}
		for row in sub_assembly_items_store:
			key = (
				row.get("production_item"),
				row.get("fg_warehouse"),
				row.get("bom_no"),
				row.get("type_of_manufacturing"),
			)
			existing_row = key_wise_data.get(key)
			if existing_row:
				self._merge_subassembly_row(existing_row, row)
			else:
				key_wise_data[key] = row

		return list(key_wise_data.values())

	@staticmethod
	def _merge_subassembly_row(existing_row, row):
		existing_row.qty += flt(row.qty)
		existing_row.stock_qty += flt(row.stock_qty)
		existing_row.bom_level = max(existing_row.bom_level, row.bom_level)

	def all_items_completed(self):
		all_items_produced = all(
			flt(d.planned_qty) - flt(d.produced_qty) < 0.000001 for d in self.doc.po_items
		)
		if not all_items_produced:
			return False

		wo_status = frappe.get_all(
			"Work Order",
			filters={
				"production_plan": self.doc.name,
				"status": ("not in", ["Closed", "Stopped"]),
				"docstatus": 1,
			},
			fields="status",
			pluck="status",
		)
		return all(s == "Completed" for s in wo_status)
