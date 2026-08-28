# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	return get_column(filters), get_data(filters)


def get_data(filters):
	plan = frappe.get_cached_doc("Production Plan", filters.get("production_plan"))
	work_orders = get_work_orders(filters)
	purchase_orders = get_purchase_orders(filters)

	data = []
	for row in plan.po_items:
		fg_work_orders = [d for d in work_orders if d.production_plan_item == row.name]
		data.append(get_finished_good_row(row, fg_work_orders))
		data.extend(get_document_row(d, indent=1) for d in fg_work_orders)
		sub_items = [d for d in plan.sub_assembly_items if d.production_plan_item == row.name]
		add_sub_assembly_rows(sub_items, data, work_orders, purchase_orders)

	po_row_names = {row.name for row in plan.po_items}
	orphan_items = [d for d in plan.sub_assembly_items if d.production_plan_item not in po_row_names]
	add_sub_assembly_rows(orphan_items, data, work_orders, purchase_orders)

	return data


def get_finished_good_row(row, fg_work_orders):
	produced_qty = sum(flt(d.produced_qty) for d in fg_work_orders)
	return {
		"indent": 0,
		"item_code": row.item_code,
		"item_name": frappe.get_cached_value("Item", row.item_code, "item_name"),
		"sales_order": row.get("sales_order"),
		"bom_level": 0,
		"qty": flt(row.planned_qty),
		"produced_qty": produced_qty,
		"pending_qty": flt(row.planned_qty) - produced_qty,
	}


def add_sub_assembly_rows(items, data, work_orders, purchase_orders):
	for item in items:
		if item.type_of_manufacturing == "Subcontract":
			documents = [d for d in purchase_orders if d.production_plan_sub_assembly_item == item.name]
		else:
			documents = [d for d in work_orders if d.production_plan_sub_assembly_item == item.name]

		indent = 1 + (item.indent or 0)
		produced_qty = sum(flt(d.produced_qty) for d in documents)
		data.append(
			{
				"indent": indent,
				"item_code": item.production_item,
				"item_name": item.item_name,
				"bom_level": item.bom_level,
				"qty": flt(item.qty),
				"produced_qty": produced_qty,
				"pending_qty": flt(item.qty) - produced_qty,
			}
		)
		data.extend(get_document_row(d, indent=indent + 1) for d in documents)


def get_document_row(doc, indent):
	return {
		"indent": indent,
		"item_code": doc.item_code,
		"item_name": doc.item_name,
		"sales_order": doc.get("sales_order"),
		"document_type": doc.document_type,
		"document_name": doc.document_name,
		"status": doc.status,
		"qty": flt(doc.qty),
		"produced_qty": flt(doc.produced_qty),
		"pending_qty": flt(doc.qty) - flt(doc.produced_qty),
	}


def get_work_orders(filters):
	work_orders = frappe.get_all(
		"Work Order",
		filters={"production_plan": filters.get("production_plan"), "docstatus": 1},
		fields=[
			"name",
			"qty",
			"produced_qty",
			"status",
			"sales_order",
			"production_item as item_code",
			"item_name",
			"production_plan_item",
			"production_plan_sub_assembly_item",
		],
	)

	for row in work_orders:
		row.document_type = "Work Order"
		row.document_name = row.name

	return work_orders


def get_purchase_orders(filters):
	po_item = frappe.qb.DocType("Purchase Order Item")
	purchase_order = frappe.qb.DocType("Purchase Order")

	purchase_orders = (
		frappe.qb.from_(po_item)
		.inner_join(purchase_order)
		.on(po_item.parent == purchase_order.name)
		.select(
			po_item.parent.as_("document_name"),
			po_item.qty.as_("order_qty"),
			po_item.received_qty,
			po_item.item_code.as_("po_item_code"),
			po_item.item_name.as_("po_item_name"),
			po_item.fg_item,
			po_item.fg_item_qty,
			po_item.production_plan_sub_assembly_item,
			purchase_order.status,
		)
		.where((po_item.production_plan == filters.get("production_plan")) & (po_item.docstatus == 1))
		.run(as_dict=True)
	)

	return [get_purchase_order_row(row) for row in purchase_orders]


def get_purchase_order_row(row):
	produced_qty = flt(row.received_qty)
	if row.fg_item:
		produced_qty = flt(row.received_qty) / (flt(row.order_qty) / flt(row.fg_item_qty) or 1)

	item_code = row.fg_item or row.po_item_code
	return frappe._dict(
		{
			"document_type": "Purchase Order",
			"document_name": row.document_name,
			"status": row.status,
			"item_code": item_code,
			"item_name": frappe.get_cached_value("Item", item_code, "item_name"),
			"qty": flt(row.fg_item_qty) if row.fg_item else flt(row.order_qty),
			"produced_qty": produced_qty,
			"production_plan_sub_assembly_item": row.production_plan_sub_assembly_item,
		}
	)


def get_column(filters):
	return [
		{
			"label": _("Item Code"),
			"fieldtype": "Link",
			"fieldname": "item_code",
			"width": 240,
			"options": "Item",
		},
		{"label": _("Item Name"), "fieldtype": "Data", "fieldname": "item_name", "width": 180},
		{
			"label": _("Sales Order"),
			"options": "Sales Order",
			"fieldtype": "Link",
			"fieldname": "sales_order",
			"width": 120,
		},
		{
			"label": _("Document Type"),
			"fieldtype": "Data",
			"fieldname": "document_type",
			"width": 120,
		},
		{
			"label": _("Document Name"),
			"fieldtype": "Dynamic Link",
			"fieldname": "document_name",
			"options": "document_type",
			"width": 180,
		},
		{"label": _("Status"), "fieldtype": "Data", "fieldname": "status", "width": 110},
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
