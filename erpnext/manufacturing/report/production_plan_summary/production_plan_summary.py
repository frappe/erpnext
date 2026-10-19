# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_column(filters)

	return columns, data


def get_data(filters):
	data = []

	order_details = {}
	get_work_order_details(filters, order_details)
	get_purchase_order_details(filters, order_details)
	get_production_plan_item_details(filters, data, order_details)

	return data


def get_production_plan_item_details(filters, data, order_details):
	production_plan_doc = frappe.get_cached_doc("Production Plan", filters.get("production_plan"))
	for row in production_plan_doc.po_items:
		work_orders = frappe.get_all(
			"Work Order",
			filters={
				"production_plan_item": row.name,
				"bom_no": row.bom_no,
				"production_item": row.item_code,
				"docstatus": 1,
			},
			order_by="creation",
			pluck="name",
		)

		order_qty = flt(row.planned_qty)
		total_produced_qty = 0.0
		# default to the full planned qty so a plan without any work order still
		# reports everything as pending rather than a misleading zero
		pending_qty = order_qty
		for work_order in work_orders:
			details = order_details.get((work_order, row.item_code), {})
			produced_qty = flt(details.get("produced_qty", 0))
			pending_qty = get_pending_qty(order_qty, produced_qty, details.get("process_loss_qty"))

			total_produced_qty += produced_qty

			data.append(
				{
					"indent": 0,
					"item_code": row.item_code,
					"sales_order": row.get("sales_order"),
					"item_name": frappe.get_cached_value("Item", row.item_code, "item_name"),
					"qty": order_qty,
					"document_type": "Work Order",
					"document_name": work_order or "",
					"bom_level": 0,
					"produced_qty": produced_qty,
					"pending_qty": pending_qty,
				}
			)

			order_qty = get_pending_qty(order_qty, produced_qty, 0)

		data.append(
			{
				"item_code": row.item_code,
				"indent": 0,
				"qty": row.planned_qty,
				"produced_qty": total_produced_qty,
				"pending_qty": get_summary_pending_qty(row, work_orders, order_details)
				if work_orders
				else pending_qty,
			}
		)

		get_production_plan_sub_assembly_item_details(filters, row, production_plan_doc, data, order_details)


def get_production_plan_sub_assembly_item_details(filters, row, production_plan_doc, data, order_details):
	for item in production_plan_doc.sub_assembly_items:
		if row.name == item.production_plan_item:
			subcontracted_item = item.type_of_manufacturing == "Subcontract"

			if subcontracted_item:
				docnames = frappe.get_all(
					"Purchase Order Item",
					filters={"production_plan_sub_assembly_item": item.name, "docstatus": 1},
					fields=["parent"],
					order_by="creation",
					pluck="parent",
				)
			else:
				docnames = frappe.get_all(
					"Work Order",
					filters={"production_plan_sub_assembly_item": item.name, "docstatus": 1},
					fields=["name"],
					order_by="creation",
					pluck="name",
				)

			remaining_qty = flt(item.qty)
			for docname in docnames:
				details = order_details.get((docname, item.production_item), {})
				produced_qty = flt(details.get("produced_qty", 0))
				data.append(
					{
						"indent": 1 + item.indent,
						"item_code": item.production_item,
						"item_name": item.item_name,
						"qty": item.qty,
						"document_type": "Work Order" if not subcontracted_item else "Purchase Order",
						"document_name": docname or "",
						"bom_level": item.bom_level,
						"produced_qty": produced_qty,
						"pending_qty": get_pending_qty(
							remaining_qty, produced_qty, details.get("process_loss_qty")
						),
					}
				)
				remaining_qty = get_pending_qty(remaining_qty, produced_qty, 0)


def get_summary_pending_qty(row, work_orders, order_details):
	details = [order_details.get((work_order, row.item_code), {}) for work_order in work_orders]
	produced_qty = sum(flt(d.get("produced_qty")) for d in details)
	ordered_beyond_plan = max(sum(flt(d.get("qty")) for d in details) - flt(row.planned_qty), 0)
	process_loss_qty = sum(flt(d.get("process_loss_qty")) for d in details)
	unreplaced_loss_qty = max(process_loss_qty - ordered_beyond_plan, 0)
	return get_pending_qty(row.planned_qty, produced_qty, unreplaced_loss_qty)


def get_pending_qty(qty, produced_qty, process_loss_qty):
	return flt(
		flt(qty) - flt(produced_qty) - flt(process_loss_qty), frappe.get_precision("Work Order", "qty")
	)


def get_work_order_details(filters, order_details):
	for row in frappe.get_all(
		"Work Order",
		filters={"production_plan": filters.get("production_plan"), "docstatus": 1},
		fields=[
			"name",
			"qty",
			"produced_qty",
			"process_loss_qty",
			"production_plan",
			"production_item",
			"sales_order",
		],
	):
		order_details.setdefault((row.name, row.production_item), row)


def get_purchase_order_details(filters, order_details):
	for row in frappe.get_all(
		"Purchase Order Item",
		filters={"production_plan": filters.get("production_plan"), "docstatus": 1},
		fields=["parent", "qty", "received_qty as produced_qty", "item_code", "fg_item", "fg_item_qty"],
	):
		if row.fg_item:
			row.produced_qty /= row.qty / row.fg_item_qty or 1
		order_details.setdefault((row.parent, row.fg_item or row.item_code), row)


def get_column(filters):
	return [
		{
			"label": _("Finished Good"),
			"fieldtype": "Link",
			"fieldname": "item_code",
			"width": 240,
			"options": "Item",
		},
		{"label": _("Item Name"), "fieldtype": "data", "fieldname": "item_name", "width": 150},
		{
			"label": _("Sales Order"),
			"options": "Sales Order",
			"fieldtype": "Link",
			"fieldname": "sales_order",
			"width": 100,
		},
		{
			"label": _("Document Type"),
			"fieldtype": "Link",
			"options": "DocType",
			"fieldname": "document_type",
			"width": 150,
		},
		{
			"label": _("Document Name"),
			"fieldtype": "Dynamic Link",
			"fieldname": "document_name",
			"options": "document_type",
			"width": 180,
		},
		{"label": _("BOM Level"), "fieldtype": "Int", "fieldname": "bom_level", "width": 100},
		{"label": _("Order Qty"), "fieldtype": "Float", "fieldname": "qty", "width": 120},
		{
			"label": _("Produced / Received Qty"),
			"fieldtype": "Float",
			"fieldname": "produced_qty",
			"width": 200,
		},
		{"label": _("Pending Qty"), "fieldtype": "Float", "fieldname": "pending_qty", "width": 110},
	]
