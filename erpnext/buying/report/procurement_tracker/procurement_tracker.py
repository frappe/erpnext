# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint,cstr

def execute(filters=None):
	columns = get_columns()
	data = get_data()
	return columns, data

def get_columns():
	columns = [
		{
			"label": _("Date Requisition Received in Procurement "),
			"fieldname": "date_requisition_received_in_procurement",
			"fieldtype": "Date",
			"width": 140
		},
		{
			"label": _("Date Requisition was Raised"),
			"fieldname": "date_requisition_was_raised",
			"fieldtype": "Date",
			"width": 140
		},
		{
			"label": _("Sector/Project"),
			"options": "Cost Center",
			"fieldname": "sector/project",
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
			"label": _("Budget Code"),
			"options": "Budget",
			"fieldname": "budget_code",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Requisition Line"),
			"options": "Item",
			"fieldname": "requisition_line",
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
			"fieldname": "purchase_order_amount",
			"fieldtype": "Float",
			"width": 140
		},
		{
			"label": _("Purchase Order Amount(USD)"),
			"fieldname": "purchase_order_amount_usd",
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

def get_data():
	purchase_order_entry = frappe.db.sql("""
		SELECT
			po_item.item_code,
			po_item.item_name,
			po_item.cost_center,
			po_item.project,
			po_item.warehouse,
			po_item.material_request,
			po_item.description,
			po_item.stock_uom,
			po_item.qty,
			po_item.net_amount,
			po_item.base_amount,
			po_item.schedule_date,
			po_item.expected_delivery_date,
			po.name,
			po.transaction_date,
			po.supplier,
			po.status,
			po.owner
		FROM `tabPurchase Order` po, `tabPurchase Order Item` po_item
		WHERE
			po.docstatus = 1
			AND po.name = po_item.parent
			AND po.status not in  ("Closed","Completed","Cancelled")
		GROUP BY
			po.name,po_item.item_code
		""", as_dict = 1)

	mr_records = frappe._dict(frappe.db.sql("""
		SELECT
			name,
			transaction_date
		FROM `tabMaterial Request`
		WHERE
			per_ordered = 100
			AND docstatus = 1
		"""))

	supplier_quotation_records = frappe._dict(frappe.db.sql("""
		SELECT
			name,
			base_amount
		FROM `tabSupplier Quotation Item`
		WHERE
			per_ordered = 100
			AND docstatus = 1
		"""))

	budget_records = frappe.db.sql("""
		SELECT
			budget.name,
			budget.project,
			budget.cost_center,
			budget_account.account,
			budget_account.budget_amount
		FROM `tabBudget` budget, `tabBudget Account` budget_account
		WHERE
			budget.project IS NOT NULL
			AND budget.name = budget_account.parent
			AND budget.cost_center IS NOT NULL
			AND budget.docstatus = 1
		""", as_dict = 1)

	return purchase_order_entry