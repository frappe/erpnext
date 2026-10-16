# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt

from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_companies_condition


def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	columns = [
		{
			"label": _("Work Order"),
			"fieldname": "work_order",
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 120,
		}
	]

	if not filters.get("bom_no"):
		columns.extend(
			[
				{
					"label": _("BOM No"),
					"fieldname": "bom_no",
					"fieldtype": "Link",
					"options": "BOM",
					"width": 180,
				}
			]
		)

	columns.extend(
		[
			{
				"label": _("Finished Good"),
				"fieldname": "production_item",
				"fieldtype": "Link",
				"options": "Item",
				"width": 120,
			},
			{"label": _("Ordered Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 120},
			{"label": _("Produced Qty"), "fieldname": "produced_qty", "fieldtype": "Float", "width": 120},
			{
				"label": _("Raw Material"),
				"fieldname": "raw_material_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 120,
			},
			{"label": _("Required Qty"), "fieldname": "required_qty", "fieldtype": "Float", "width": 120},
			{"label": _("Consumed Qty"), "fieldname": "consumed_qty", "fieldtype": "Float", "width": 120},
		]
	)

	return columns


def get_data(filters):
	wo = frappe.qb.DocType("Work Order")
	query = get_work_order_query(["name as work_order", "qty", "produced_qty", "production_item", "bom_no"])

	if filters.get("bom_no") and not filters.get("work_order"):
		query = query.where(wo.bom_no == filters.get("bom_no"))

	if filters.get("work_order"):
		query = query.where(wo.name == filters.get("work_order"))

	work_orders = query.run(as_dict=True)
	materials = get_materials_by_work_order([d.work_order for d in work_orders])

	results = []
	for d in work_orders:
		results.append(d)
		for data in materials.get(d.work_order, []):
			data.required_qty = flt(data.required_qty) * flt(d.produced_qty) / flt(d.qty)
			results.append(data)

	return results


def get_work_order_query(fields):
	wo = frappe.qb.DocType("Work Order")
	query = frappe.qb.get_query(
		"Work Order",
		fields=fields,
		filters={"docstatus": 1, "produced_qty": [">", 0]},
		ignore_permissions=False,
	)

	if condition := get_allowed_companies_condition(wo.company, "Work Order"):
		query = query.where(condition)

	return query


def get_materials_by_work_order(work_orders):
	if not work_orders:
		return {}

	materials = {}
	for row in frappe.get_all(
		"Work Order Item",
		fields=["parent", "item_code as raw_material_code", "required_qty", "consumed_qty"],
		filters={"parent": ["in", work_orders], "parenttype": "Work Order"},
		order_by="idx",
	):
		materials.setdefault(row.pop("parent"), []).append(row)

	return materials


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_work_orders(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	wo = frappe.qb.DocType("Work Order")
	query = (
		get_work_order_query(["name"])
		.where(wo.name.like(f"{txt}%"))
		.orderby(wo.name)
		.limit(page_len)
		.offset(start)
	)

	if filters.get("bom_no"):
		query = query.where(wo.bom_no == filters.get("bom_no"))

	return query.run(as_list=True)
