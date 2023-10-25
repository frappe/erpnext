# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	columns = [
		{
			"label": _("Material Request Date"),
			"fieldname": "material_request_date",
			"fieldtype": "Date",
			"width": 140,
		},
		{
			"label": _("Material Request No"),
			"options": "Material Request",
			"fieldname": "material_request_no",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Cost Center"),
			"options": "Cost Center",
			"fieldname": "cost_center",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Project"),
			"options": "Project",
			"fieldname": "project",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Requesting Site"),
			"options": "Warehouse",
			"fieldname": "requesting_site",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Requestor"),
			"options": "Employee",
			"fieldname": "requestor",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"label": _("Quantity"), "fieldname": "quantity", "fieldtype": "Float", "width": 140},
		{
			"label": _("Unit of Measure"),
			"options": "UOM",
			"fieldname": "unit_of_measurement",
			"fieldtype": "Link",
			"width": 140,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "data", "width": 140},
		{
			"label": _("Purchase Order Date"),
			"fieldname": "purchase_order_date",
			"fieldtype": "Date",
			"width": 140,
		},
		{
			"label": _("Purchase Order"),
			"options": "Purchase Order",
			"fieldname": "purchase_order",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Supplier"),
			"options": "Supplier",
			"fieldname": "supplier",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Estimated Cost"),
			"fieldname": "estimated_cost",
			"fieldtype": "Float",
			"width": 140,
		},
		{"label": _("Actual Cost"), "fieldname": "actual_cost", "fieldtype": "Float", "width": 140},
		{
			"label": _("Purchase Order Amount"),
			"fieldname": "purchase_order_amt",
			"fieldtype": "Float",
			"width": 140,
		},
		{
			"label": _("Purchase Order Amount(Company Currency)"),
			"fieldname": "purchase_order_amt_in_company_currency",
			"fieldtype": "Float",
			"width": 140,
		},
		{
			"label": _("Expected Delivery Date"),
			"fieldname": "expected_delivery_date",
			"fieldtype": "Date",
			"width": 140,
		},
		{
			"label": _("Actual Delivery Date"),
			"fieldname": "actual_delivery_date",
			"fieldtype": "Date",
			"width": 140,
		},
	]
	return columns


def apply_filters_on_query(filters, parent, child, query):
	if filters.get("company"):
		query = query.where(parent.company == filters.get("company"))

	if filters.get("cost_center") or filters.get("project"):
		query = query.where(
			(child.cost_center == filters.get("cost_center")) | (child.project == filters.get("project"))
		)

	if filters.get("from_date"):
		query = query.where(parent.transaction_date >= filters.get("from_date"))

	if filters.get("to_date"):
		query = query.where(parent.transaction_date <= filters.get("to_date"))

	return query


def get_data(filters):
	purchase_order_entry = get_po_entries(filters)
	mr_records, procurement_record_against_mr = get_mapped_mr_details(filters)
	pr_records = get_mapped_pr_records()
	pi_records = get_mapped_pi_records()

	procurement_record = []
	if procurement_record_against_mr:
		procurement_record += procurement_record_against_mr

	for po in purchase_order_entry:
		# fetch material records linked to the purchase order item
		material_requests = mr_records.get(po.material_request_item, [{}])

		for mr_record in material_requests:
			procurement_detail = {
				"material_request_date": mr_record.get("transaction_date"),
				"cost_center": po.cost_center,
				"project": po.project,
				"requesting_site": po.warehouse,
				"requestor": po.owner,
				"material_request_no": po.material_request,
				"item_code": po.item_code,
				"quantity": flt(po.qty),
				"unit_of_measurement": po.stock_uom,
				"status": po.status,
				"purchase_order_date": po.transaction_date,
				"purchase_order": po.parent,
				"supplier": po.supplier,
				"estimated_cost": flt(mr_record.get("amount")),
				"actual_cost": flt(pi_records.get(po.name)),
				"purchase_order_amt": flt(po.amount),
				"purchase_order_amt_in_company_currency": flt(po.base_amount),
				"expected_delivery_date": po.schedule_date,
				"actual_delivery_date": pr_records.get(po.name),
			}
			procurement_record.append(procurement_detail)

	return procurement_record


def get_mapped_mr_details(filters):
	mr_records = {}
	parent = frappe.qb.DocType("Material Request")
	child = frappe.qb.DocType("Material Request Item")

	query = (
		frappe.qb.from_(parent)
		.from_(child)
		.select(
			parent.transaction_date,
			parent.per_ordered,
			parent.owner,
			child.name,
			child.parent,
			child.amount,
			child.qty,
			child.item_code,
			child.uom,
			parent.status,
			child.project,
			child.cost_center,
		)
		.where((parent.per_ordered >= 0) & (parent.name == child.parent) & (parent.docstatus == 1))
	)
	query = apply_filters_on_query(filters, parent, child, query)

	mr_details = query.run(as_dict=True)

	procurement_record_against_mr = []
	for record in mr_details:
		if record.per_ordered:
			mr_records.setdefault(record.name, []).append(frappe._dict(record))
		else:
			procurement_record_details = dict(
				material_request_date=record.transaction_date,
				material_request_no=record.parent,
				requestor=record.owner,
				item_code=record.item_code,
				estimated_cost=flt(record.amount),
				quantity=flt(record.qty),
				unit_of_measurement=record.uom,
				status=record.status,
				actual_cost=0,
				purchase_order_amt=0,
				purchase_order_amt_in_company_currency=0,
				project=record.project,
				cost_center=record.cost_center,
			)
			procurement_record_against_mr.append(procurement_record_details)
	return mr_records, procurement_record_against_mr


def get_mapped_pi_records():
	po = frappe.qb.DocType("Purchase Order")
	pi_item = frappe.qb.DocType("Purchase Invoice Item")
	pi_records = (
		frappe.qb.from_(pi_item)
		.inner_join(po)
		.on(pi_item.purchase_order == po.name)
		.select(pi_item.po_detail, pi_item.base_amount)
		.where(
			(pi_item.docstatus == 1)
			& (po.status.notin(("Closed", "Completed", "Cancelled")))
			& (pi_item.po_detail.isnotnull())
		)
	).run()

	return frappe._dict(pi_records)


def get_mapped_pr_records():
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")
	pr_records = (
		frappe.qb.from_(pr)
		.from_(pr_item)
		.select(pr_item.purchase_order_item, pr.posting_date)
		.where(
			(pr.docstatus == 1)
			& (pr.name == pr_item.parent)
			& (pr_item.purchase_order_item.isnotnull())
			& (pr.status.notin(("Closed", "Completed", "Cancelled")))
		)
	).run()

	return frappe._dict(pr_records)


def get_po_entries(filters):
	parent = frappe.qb.DocType("Purchase Order")
	child = frappe.qb.DocType("Purchase Order Item")

	query = (
		frappe.qb.from_(parent)
		.from_(child)
		.select(
			child.name,
			child.parent,
			child.cost_center,
			child.project,
			child.warehouse,
			child.material_request,
			child.material_request_item,
			child.item_code,
			child.stock_uom,
			child.qty,
			child.amount,
			child.base_amount,
			child.schedule_date,
			parent.transaction_date,
			parent.supplier,
			parent.status,
			parent.owner,
		)
		.where(
			(parent.docstatus == 1)
			& (parent.name == child.parent)
			& (parent.status.notin(("Closed", "Completed", "Cancelled")))
		)
		.groupby(parent.name, child.material_request_item)
	)
	query = apply_filters_on_query(filters, parent, child, query)

	return query.run(as_dict=True)
