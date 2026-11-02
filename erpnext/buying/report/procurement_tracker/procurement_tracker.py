# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Max, Sum
from frappe.utils import flt

from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_companies_condition


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
			"options": "User",
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

	if filters.get("cost_center"):
		query = query.where(child.cost_center == filters.get("cost_center"))

	if filters.get("project"):
		query = query.where(child.project == filters.get("project"))

	if filters.get("from_date"):
		query = query.where(parent.transaction_date >= filters.get("from_date"))

	if filters.get("to_date"):
		query = query.where(parent.transaction_date <= filters.get("to_date"))

	return query


def get_data(filters):
	purchase_order_entry = get_po_entries(filters)
	request_items = {po.material_request_item for po in purchase_order_entry if po.material_request_item}
	mr_records, procurement_record_against_mr = get_mapped_mr_details(filters, request_items)
	pr_records = get_mapped_pr_records()
	pi_records = get_mapped_pi_records(filters)
	ordered_qty_by_request_item = get_ordered_qty_by_request_item(request_items)

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
				"requestor": mr_record.get("owner", po.owner),
				"material_request_no": po.material_request,
				"item_code": po.item_code,
				"quantity": flt(po.qty),
				"unit_of_measurement": po.uom,
				"status": po.status,
				"purchase_order_date": po.transaction_date,
				"purchase_order": po.parent,
				"supplier": po.supplier,
				"estimated_cost": get_estimated_cost(po, mr_record, ordered_qty_by_request_item),
				"actual_cost": get_actual_cost(po, pi_records),
				"purchase_order_amt": flt(po.amount),
				"purchase_order_amt_in_company_currency": flt(po.base_amount),
				"expected_delivery_date": po.schedule_date,
				"actual_delivery_date": pr_records.get(po.name),
			}
			procurement_record.append(procurement_detail)

	return procurement_record


def get_ordered_qty_by_request_item(request_items):
	if not request_items:
		return {}

	parent = frappe.qb.DocType("Purchase Order")
	child = frappe.qb.DocType("Purchase Order Item")
	return dict(
		frappe.qb.from_(child)
		.inner_join(parent)
		.on(child.parent == parent.name)
		.select(child.material_request_item, Sum(get_request_qty_column(parent, child)))
		.where((child.docstatus == 1) & (child.material_request_item.isin(list(request_items))))
		.groupby(child.material_request_item)
		.run()
	)


def get_request_qty_column(parent, child):
	"""Order line quantity in its request's unit: finished goods for subcontracting."""
	return Case().when(parent.is_subcontracted == 1, child.fg_item_qty).else_(child.stock_qty)


def get_actual_cost(po, pi_records):
	"""Invoiced amount, or the line amount while the order can still be billed."""
	if po.name in pi_records:
		return flt(pi_records[po.name])
	return 0.0 if po.status == "Closed" else flt(po.base_amount)


def get_estimated_cost(po, mr_record, ordered_qty_by_request_item):
	"""Request item amount shared across all its submitted Purchase Order lines by ordered qty."""
	ordered_qty = flt(ordered_qty_by_request_item.get(po.material_request_item))
	if not ordered_qty:
		return flt(mr_record.get("amount"))
	return flt(mr_record.get("amount")) * (flt(po.request_qty) / ordered_qty)


def get_mapped_mr_details(filters, request_items):
	parent = frappe.qb.DocType("Material Request")
	child = frappe.qb.DocType("Material Request Item")

	query = (
		frappe.qb.from_(parent)
		.from_(child)
		.select(
			parent.transaction_date,
			parent.owner,
			child.name,
			child.parent,
			child.amount,
			child.qty,
			child.ordered_qty,
			child.item_code,
			child.uom,
			parent.status,
			child.project,
			child.cost_center,
		)
		.where(
			(parent.per_ordered >= 0)
			& (parent.name == child.parent)
			& (parent.docstatus == 1)
			& (parent.material_request_type.isin(("Purchase", "Subcontracting")))
		)
	)
	if condition := get_allowed_companies_condition(parent.company, "Material Request"):
		query = query.where(condition)

	mr_records = {}
	if request_items:
		for record in query.where(child.name.isin(list(request_items))).run(as_dict=True):
			mr_records.setdefault(record.name, []).append(record)

	unordered_query = apply_filters_on_query(filters, parent, child, query).where(child.ordered_qty == 0)
	procurement_record_against_mr = []
	for record in unordered_query.run(as_dict=True):
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


def get_hidden_order_statuses(filters):
	if filters.get("show_completed_orders"):
		return ("Cancelled",)
	return ("Closed", "Completed", "Cancelled")


def get_mapped_pi_records(filters):
	po = frappe.qb.DocType("Purchase Order")
	pi_item = frappe.qb.DocType("Purchase Invoice Item")
	pi_records = (
		frappe.qb.from_(pi_item)
		.inner_join(po)
		.on(pi_item.purchase_order == po.name)
		.select(pi_item.po_detail, Sum(pi_item.base_amount))
		.where(
			(pi_item.docstatus == 1)
			& (po.status.notin(get_hidden_order_statuses(filters)))
			& (pi_item.po_detail.isnotnull())
		)
		.groupby(pi_item.po_detail)
	).run()

	return frappe._dict(pi_records)


def get_mapped_pr_records():
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")
	pr_records = (
		frappe.qb.from_(pr)
		.from_(pr_item)
		.select(pr_item.purchase_order_item, Max(pr.posting_date))
		.where(
			(pr.docstatus == 1)
			& (pr.is_return == 0)
			& (pr.name == pr_item.parent)
			& (pr_item.purchase_order_item.isnotnull())
		)
		.groupby(pr_item.purchase_order_item)
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
			child.uom,
			child.qty,
			child.amount,
			child.base_amount,
			get_request_qty_column(parent, child).as_("request_qty"),
			child.schedule_date,
			parent.transaction_date,
			parent.supplier,
			parent.status,
			parent.owner,
		)
		.where(
			(parent.docstatus == 1)
			& (parent.name == child.parent)
			& (parent.status.notin(get_hidden_order_statuses(filters)))
		)
	)
	query = apply_filters_on_query(filters, parent, child, query)
	if condition := get_allowed_companies_condition(parent.company, "Purchase Order"):
		query = query.where(condition)

	return query.run(as_dict=True)
