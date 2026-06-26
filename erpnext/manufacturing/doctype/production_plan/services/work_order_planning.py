# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Work Order / subcontract PO creation from a Production Plan (extracted from production_plan.py)."""

from collections import defaultdict

import frappe
from frappe import _, msgprint
from frappe.utils import flt, get_filtered_list_link, getdate, nowdate

from erpnext.manufacturing.doctype.production_plan.services.planning_queries import set_default_warehouses

_SUB_ASSEMBLY_WO_FIELDS = [
	"production_item",
	"item_name",
	"fg_warehouse",
	"description",
	"bom_no",
	"stock_uom",
	"bom_level",
	"schedule_date",
	"sales_order",
	"sales_order_item",
]
_SUBCONTRACT_PO_ITEM_FIELDS = [
	"schedule_date",
	"qty",
	"description",
	"production_plan_item",
	"sales_order",
	"sales_order_item",
]


class WorkOrderCreationService:
	def __init__(self, doc):
		self.doc = doc

	def get_production_items(self):
		item_dict = {}
		for d in self.doc.po_items:
			item_details = self._production_item_details(d)
			if self.doc.get_items_from == "Material Request":
				item_details["qty"] = d.planned_qty
				key = (d.item_code, d.material_request_item, d.warehouse, d.planned_start_date)
				item_dict[key] = item_details
			else:
				key = self._production_item_key(d)
				existing = flt(item_dict.get(key, {}).get("qty"))
				item_details["qty"] = existing + (flt(d.planned_qty) - flt(d.ordered_qty))
				item_dict[key] = item_details
		return item_dict

	def _production_item_details(self, d):
		details = {
			"production_item": d.item_code,
			"use_multi_level_bom": d.include_exploded_items,
			"sales_order": d.sales_order,
			"sales_order_item": d.sales_order_item,
			"material_request": d.material_request,
			"material_request_item": d.material_request_item,
			"bom_no": d.bom_no,
			"description": d.description,
			"stock_uom": d.stock_uom,
			"company": self.doc.company,
			"fg_warehouse": d.warehouse,
			"production_plan": self.doc.name,
			"production_plan_item": d.name,
			"product_bundle_item": d.product_bundle_item,
			"planned_start_date": d.planned_start_date,
			"project": self.doc.project,
			"source_warehouse": frappe.get_value("BOM", d.bom_no, "default_source_warehouse"),
		}
		if not details["project"] and d.sales_order:
			details["project"] = frappe.get_cached_value("Sales Order", d.sales_order, "project")
		return details

	def _production_item_key(self, d):
		if not d.sales_order:
			return (d.name, d.item_code, d.warehouse, d.planned_start_date)
		if self.doc.combine_items:
			return (d.item_code, d.sales_order, d.warehouse, d.planned_start_date)
		return (d.item_code, d.sales_order, d.sales_order_item, d.warehouse, d.planned_start_date)

	def make_work_order(self):
		from erpnext.manufacturing.doctype.work_order.work_order import get_default_warehouse

		wo_list, po_list = [], []
		subcontracted_po = {}
		default_warehouses = get_default_warehouse(self.doc.company)

		self.make_work_order_for_finished_goods(wo_list, default_warehouses)
		self.make_work_order_for_subassembly_items(wo_list, subcontracted_po, default_warehouses)
		self.make_subcontracted_purchase_order(subcontracted_po, po_list)
		self.show_list_created_message("Work Order", wo_list)
		self.show_list_created_message("Purchase Order", po_list)

		if not wo_list:
			frappe.msgprint(_("No Work Orders were created"))
		if not po_list:
			frappe.msgprint(_("No Purchase Orders were created"))

	def make_work_order_for_finished_goods(self, wo_list, default_warehouses):
		for _key, item in self.get_production_items().items():
			if self.doc.sub_assembly_items:
				item["use_multi_level_bom"] = 0

			set_default_warehouses(item, default_warehouses)
			work_order = self.create_work_order(item)
			if work_order:
				wo_list.append(work_order)

	def make_work_order_for_subassembly_items(self, wo_list, subcontracted_po, default_warehouses):
		for row in self.doc.sub_assembly_items:
			if row.type_of_manufacturing == "Subcontract":
				subcontracted_po.setdefault(row.supplier, []).append(row)
				continue
			if row.type_of_manufacturing == "Material Request":
				continue

			work_order = self._sub_assembly_work_order(row, default_warehouses)
			if work_order:
				wo_list.append(work_order)

	def _sub_assembly_work_order(self, row, default_warehouses):
		if flt(row.qty) <= flt(row.ordered_qty):
			return None

		work_order_data = {
			"source_warehouse": frappe.get_value("BOM", row.bom_no, "default_source_warehouse"),
			"wip_warehouse": default_warehouses.get("wip_warehouse"),
			"fg_warehouse": default_warehouses.get("fg_warehouse"),
			"scrap_warehouse": default_warehouses.get("scrap_warehouse"),
			"company": self.doc.get("company"),
		}
		self.prepare_data_for_sub_assembly_items(row, work_order_data)
		if work_order_data.get("qty") <= 0:
			return None
		return self.create_work_order(work_order_data)

	def prepare_data_for_sub_assembly_items(self, row, wo_data):
		for field in _SUB_ASSEMBLY_WO_FIELDS:
			if row.get(field):
				wo_data[field] = row.get(field)

		wo_data["qty"] = flt(row.get("qty")) - flt(row.get("ordered_qty"))
		wo_data.update(
			{
				"use_multi_level_bom": 0,
				"production_plan": self.doc.name,
				"production_plan_sub_assembly_item": row.name,
			}
		)

	def make_subcontracted_purchase_order(self, subcontracted_po, purchase_orders):
		if not subcontracted_po:
			return

		subcontracted_po = _consolidate_subcontracted_po(subcontracted_po)
		for supplier, po_list in subcontracted_po.items():
			po = self._create_subcontract_po(supplier, po_list)
			purchase_orders.append(po.name)

	def _create_subcontract_po(self, supplier, po_list):
		po = frappe.new_doc("Purchase Order")
		po.company = self.doc.company
		po.supplier = supplier
		po.schedule_date = getdate(po_list[0].schedule_date) if po_list[0].schedule_date else nowdate()
		po.is_subcontracted = 1
		for row in po_list:
			po.append("items", self._subcontract_po_item(row))

		po.set_service_items_for_finished_goods()
		po.set_missing_values()
		po.flags.ignore_mandatory = True
		po.flags.ignore_validate = True
		po.insert()
		return po

	def _subcontract_po_item(self, row):
		po_data = {
			"fg_item": row.production_item,
			"warehouse": row.fg_warehouse,
			"production_plan_sub_assembly_item": row.name,
			"bom": row.bom_no,
			"production_plan": self.doc.name,
			"fg_item_qty": row.qty,
		}
		for field in _SUBCONTRACT_PO_ITEM_FIELDS:
			po_data[field] = row.get(field)
		return po_data

	def show_list_created_message(self, doctype, doc_list=None):
		if not doc_list:
			return

		frappe.flags.mute_messages = False
		msgprint(_("{0} created").format(get_filtered_list_link(doctype, doc_list)))

	def create_work_order(self, item):
		from erpnext.manufacturing.doctype.work_order.work_order import OverProductionError

		if flt(item.get("qty")) <= 0:
			return

		wo = self._new_work_order(item)
		try:
			wo.flags.ignore_mandatory = True
			wo.flags.ignore_validate = True
			wo.company = self.doc.company
			wo.insert()
			return wo.name
		except OverProductionError:
			pass

	def _new_work_order(self, item):
		wo = frappe.new_doc("Work Order")
		wo.update(item)
		if not wo.source_warehouse:
			wo.source_warehouse = item.get("fg_warehouse")

		wo.reserve_stock = self.doc.reserve_stock
		wo.planned_start_date = item.get("planned_start_date") or item.get("schedule_date")
		if item.get("warehouse"):
			wo.fg_warehouse = item.get("warehouse")

		wo.set_work_order_operations()
		wo.set_required_items(reset_source_warehouse=True)
		return wo


def _consolidate_subcontracted_po(subcontracted_po):
	items_to_remove = defaultdict(list)
	for supplier, items in subcontracted_po.items():
		for item in items:
			if item.qty == item.received_qty:
				items_to_remove[supplier].append(item)
			elif item.received_qty:
				item.qty -= item.received_qty

		subcontracted_po[supplier] = [item for item in items if item not in items_to_remove[supplier]]
	return {key: value for key, value in subcontracted_po.items() if value}
