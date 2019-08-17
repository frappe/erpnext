# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

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
			"width": 140
		},
		{
			"label": _("Material Request No"),
			"options": "Material Request",
			"fieldname": "material_request_no",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Cost Center"),
			"options": "Cost Center",
			"fieldname": "cost_center",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Project"),
			"options": "Project",
			"fieldname": "project",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Requesting Site"),
			"options": "Warehouse",
			"fieldname": "requesting_site",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Requestor"),
			"options": "Employee",
			"fieldname": "requestor",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Quantity"),
			"fieldname": "quantity",
			"fieldtype": "Int",
			"width": 140
		},
		{
			"label": _("Unit of Measure"),
			"options": "UOM",
			"fieldname": "unit_of_measurement",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "data",
			"width": 140
		},
		{
			"label": _("Purchase Order Date"),
			"fieldname": "purchase_order_date",
			"fieldtype": "Date",
			"width": 140
		},
		{
			"label": _("Purchase Order"),
			"options": "Purchase Order",
			"fieldname": "purchase_order",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Supplier"),
			"options": "Supplier",
			"fieldname": "supplier",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Estimated Cost"),
			"fieldname": "estimated_cost",
			"fieldtype": "Float",
			"width": 140
		},
		{
			"label": _("Actual Cost"),
			"fieldname": "actual_cost",
			"fieldtype": "Float",
			"width": 140
		},
		{
			"label": _("Purchase Order Amount"),
			"fieldname": "purchase_order_amt",
			"fieldtype": "Float",
			"width": 140
		},
		{
			"label": _("Purchase Order Amount(Company Currency)"),
			"fieldname": "purchase_order_amt_usd",
			"fieldtype": "Float",
			"width": 140
		},
		{
			"label": _("Expected Delivery Date"),
			"fieldname": "expected_delivery_date",
			"fieldtype": "Date",
			"width": 140
		},
		{
			"label": _("Actual Delivery Date"),
			"fieldname": "actual_delivery_date",
			"fieldtype": "Date",
			"width": 140
		},
	]
	return columns

def get_conditions(filters):
	conditions = ""

	if filters.get("company"):
		conditions += " AND company='%s'"% filters.get('company')

	if filters.get("cost_center") or filters.get("project"):
		conditions += """
			AND (cost_center='%s'
			OR project='%s')
			"""% (filters.get('cost_center'), filters.get('project'))

	if filters.get("from_date"):
		conditions += " AND transaction_date>=%s"% filters.get('from_date')

	if filters.get("to_date"):
		conditions += " AND transaction_date<=%s"% filters.get('to_date')
	return conditions

def get_data(filters):
	conditions = get_conditions(filters)
	purchase_order_entry = get_po_entries(conditions)
	mr_records, procurement_record_against_mr = get_mapped_mr_details(conditions)
	pr_records = get_mapped_pr_records()
	pi_records = get_mapped_pi_records()
	print(pi_records)

	procurement_record=[]
	if procurement_record_against_mr:
		procurement_record += procurement_record_against_mr
	for po in purchase_order_entry:
		# fetch material records linked to the purchase order item
		mr_record = mr_records.get(po.material_request_item, [{}])[0]
		procurement_detail = {
			"material_request_date": mr_record.get('transaction_date'),
			"cost_center": po.cost_center,
			"project": po.project,
			"requesting_site": po.warehouse,
			"requestor": po.owner,
			"material_request_no": po.material_request,
			"description": po.description,
			"quantity": po.qty,
			"unit_of_measurement": po.stock_uom,
			"status": po.status,
			"purchase_order_date": po.transaction_date,
			"purchase_order": po.parent,
			"supplier": po.supplier,
			"estimated_cost": mr_record.get('amount'),
			"actual_cost": pi_records.get(po.name),
			"purchase_order_amt": po.amount,
			"purchase_order_amt_in_company_currency": po.base_amount,
			"expected_delivery_date": po.schedule_date,
			"actual_delivery_date": pr_records.get(po.name)
		}
		procurement_record.append(procurement_detail)
	return procurement_record

def get_mapped_mr_details(conditions):
	mr_records = {}
	mr_details = frappe.db.sql("""
		SELECT
			mr.transaction_date,
			mr.per_ordered,
			mr_item.name,
			mr_item.parent,
			mr_item.amount
		FROM `tabMaterial Request` mr, `tabMaterial Request Item` mr_item
		WHERE
			mr.per_ordered>=0
			AND mr.name=mr_item.parent
			AND mr.docstatus=1
			{conditions}
		""".format(conditions=conditions), as_dict=1) #nosec

	procurement_record_against_mr = []
	for record in mr_details:
		if record.per_ordered:
			mr_records.setdefault(record.name, []).append(frappe._dict(record))
		else:
			procurement_record_details = dict(
				material_request_date=record.transaction_date,
				material_request_no=record.parent,
				estimated_cost=record.amount
			)
			procurement_record_against_mr.append(procurement_record_details)
	return mr_records, procurement_record_against_mr

def get_mapped_pi_records():
	return frappe._dict(frappe.db.sql("""
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
		"""))

def get_mapped_pr_records():
	return frappe._dict(frappe.db.sql("""
		SELECT
			pr_item.purchase_order_item,
			pr.posting_date
		FROM `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pr_item
		WHERE
			pr.docstatus=1
			AND pr.name=pr_item.parent
			AND pr_item.purchase_order_item IS NOT NULL
			AND pr.status not in  ("Closed","Completed","Cancelled")
		"""))

def get_po_entries(conditions):
	return frappe.db.sql("""
		SELECT
			po_item.name,
			po_item.parent,
			po_item.cost_center,
			po_item.project,
			po_item.warehouse,
			po_item.material_request,
			po_item.material_request_item,
			po_item.description,
			po_item.stock_uom,
			po_item.qty,
			po_item.amount,
			po_item.base_amount,
			po_item.schedule_date,
			po.transaction_date,
			po.supplier,
			po.status,
			po.owner
		FROM `tabPurchase Order` po, `tabPurchase Order Item` po_item
		WHERE
			po.docstatus = 1
			AND po.name = po_item.parent
			AND po.status not in  ("Closed","Completed","Cancelled")
			{conditions}
		GROUP BY
			po.name,po_item.item_code
		""".format(conditions=conditions), as_dict=1) #nosec