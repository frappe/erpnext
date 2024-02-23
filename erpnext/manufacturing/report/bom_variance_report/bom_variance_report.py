# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


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
	query = (
		frappe.qb.from_(wo)
		.select(wo.name.as_("work_order"), wo.qty, wo.produced_qty, wo.production_item, wo.bom_no)
		.where((wo.produced_qty > wo.qty) & (wo.docstatus == 1))
	)

	if filters.get("bom_no") and not filters.get("work_order"):
		query = query.where(wo.bom_no == filters.get("bom_no"))

	if filters.get("work_order"):
		query = query.where(wo.name == filters.get("work_order"))

	results = []
	for d in query.run(as_dict=True):
		results.append(d)

		for data in frappe.get_all(
			"Work Order Item",
			fields=["item_code as raw_material_code", "required_qty", "consumed_qty"],
			filters={"parent": d.work_order, "parenttype": "Work Order"},
		):
			results.append(data)

	return results


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_work_orders(doctype, txt, searchfield, start, page_len, filters):
	wo = frappe.qb.DocType("Work Order")
	query = (
		frappe.qb.from_(wo)
		.select(wo.name)
		.where((wo.name.like(f"{txt}%")) & (wo.produced_qty > wo.qty) & (wo.docstatus == 1))
		.orderby(wo.name)
		.limit(page_len)
		.offset(start)
	)

	if filters.get("bom_no"):
		query = query.where(wo.bom_no == filters.get("bom_no"))

	return query.run(as_list=True)
