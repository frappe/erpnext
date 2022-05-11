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


def get_conditions(filters):
	conditions = ""

	if filters.get("company"):
		conditions += " AND parent.company=%s" % frappe.db.escape(filters.get("company"))

	if filters.get("cost_center") or filters.get("project"):
		conditions += """
			AND (child.`cost_center`=%s OR child.`project`=%s)
			""" % (
			frappe.db.escape(filters.get("cost_center")),
			frappe.db.escape(filters.get("project")),
		)

	if filters.get("from_date"):
		conditions += " AND parent.transaction_date>='%s'" % filters.get("from_date")

	if filters.get("to_date"):
		conditions += " AND parent.transaction_date<='%s'" % filters.get("to_date")
	return conditions


def get_data(filters):
	conditions = get_conditions(filters)
	purchase_order_entry = get_po_entries(conditions)
	mr_records, procurement_record_against_mr = get_mapped_mr_details(conditions)
	pr_records = get_mapped_pr_records()
	pi_records = get_mapped_pi_records()

	procurement_record = []
	if procurement_record_against_mr:
		procurement_record += procurement_record_against_mr
	for po in purchase_order_entry:
		# fetch material records linked to the purchase order item
		mr_record = mr_records.get(po.material_request_item, [{}])[0]
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


def get_mapped_mr_details(conditions):
	mr_records = {}
	mr_details = frappe.db.sql(
		"""
		SELECT
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
			child.cost_center
		FROM `tabMaterial Request` parent, `tabMaterial Request Item` child
		WHERE
			parent.per_ordered>=0
			AND parent.name=child.parent
			AND parent.docstatus=1
			{conditions}
		""".format(
			conditions=conditions
		),
		as_dict=1,
	)  # nosec

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
	return frappe._dict(
		frappe.db.sql(
			"""
		SELECT
			pi_item.po_detail,
			pi_item.base_amount
		FROM `tabPurchase Invoice Item` as pi_item
		INNER JOIN `tabPurchase Order` as po
		ON pi_item.`purchase_order` = po.`name`
		WHERE
			pi_item.docstatus = 1
			AND po.status not in ("Closed","Completed","Cancelled")
			AND pi_item.po_detail IS NOT NULL
		"""
		)
	)


def get_mapped_pr_records():
	return frappe._dict(
		frappe.db.sql(
			"""
		SELECT
			pr_item.purchase_order_item,
			pr.posting_date
		FROM `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pr_item
		WHERE
			pr.docstatus=1
			AND pr.name=pr_item.parent
			AND pr_item.purchase_order_item IS NOT NULL
			AND pr.status not in  ("Closed","Completed","Cancelled")
		"""
		)
	)


def get_po_entries(conditions):
	return frappe.db.sql(
		"""
		SELECT
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
			parent.owner
		FROM `tabPurchase Order` parent, `tabPurchase Order Item` child
		WHERE
			parent.docstatus = 1
			AND parent.name = child.parent
			AND parent.status not in  ("Closed","Completed","Cancelled")
			{conditions}
		GROUP BY
			parent.name, child.item_code
		""".format(
			conditions=conditions
		),
		as_dict=1,
	)  # nosec
