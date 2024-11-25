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
			},
			pluck="name",
		)

		order_qty = row.planned_qty
		total_produced_qty = 0.0
		pending_qty = 0.0
		for work_order in work_orders:
			produced_qty = flt(order_details.get((work_order, row.item_code), {}).get("produced_qty", 0))
			pending_qty = flt(order_qty) - produced_qty

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

			order_qty = pending_qty

		data.append(
			{
				"item_code": row.item_code,
				"indent": 0,
				"qty": row.planned_qty,
				"produced_qty": total_produced_qty,
				"pending_qty": pending_qty,
			}
		)

		get_production_plan_sub_assembly_item_details(filters, row, production_plan_doc, data, order_details)


def get_production_plan_sub_assembly_item_details(filters, row, production_plan_doc, data, order_details):
	for item in production_plan_doc.sub_assembly_items:
		if row.name == item.production_plan_item:
			subcontracted_item = item.type_of_manufacturing == "Subcontract"

			if subcontracted_item:
				docname = frappe.get_value(
					"Purchase Order Item",
					{"production_plan_sub_assembly_item": item.name, "docstatus": ("<", 2)},
					"parent",
				)
			else:
				docname = frappe.get_value(
					"Work Order",
					{"production_plan_sub_assembly_item": item.name, "docstatus": ("<", 2)},
					"name",
				)

			data.append(
				{
					"indent": 1 + item.indent,
					"item_code": item.production_item,
					"item_name": item.item_name,
					"qty": item.qty,
					"document_type": "Work Order" if not subcontracted_item else "Purchase Order",
					"document_name": docname or "",
					"bom_level": item.bom_level,
					"produced_qty": order_details.get((docname, item.production_item), {}).get(
						"produced_qty", 0
					),
					"pending_qty": flt(item.qty)
					- flt(order_details.get((docname, item.production_item), {}).get("produced_qty", 0)),
				}
			)


def get_work_order_details(filters, order_details):
	for row in frappe.get_all(
		"Work Order",
		filters={"production_plan": filters.get("production_plan")},
		fields=["name", "produced_qty", "production_plan", "production_item", "sales_order"],
	):
		order_details.setdefault((row.name, row.production_item), row)


def get_purchase_order_details(filters, order_details):
	for row in frappe.get_all(
		"Purchase Order Item",
		filters={"production_plan": filters.get("production_plan")},
		fields=["parent", "received_qty as produced_qty", "item_code"],
	):
		order_details.setdefault((row.parent, row.item_code), row)


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
			"fieldname": "document_type",
			"width": 150,
			"options": "DocType",
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
