# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	columns=get_columns()
	data=get_sales_payment_data(filters, columns)
	return columns, data

def get_columns():
	return [
		_("Date") + ":Date:80",
		_("Owner") + "::150",
		_("Payment Mode") + "::120",
		_("Warehouse") + ":Link/Cost Center:100",
		_("Cost Center") + ":Link/Warehouse:100",
		_("Sales and Returns") + ":Currency/currency:120",
		_("Taxes") + ":Currency/currency:120",
		_("Payments") + ":Currency/currency:120",
		_("Reconciliation") + ":Currency/currency:120"
	]

def get_sales_payment_data(filters, columns):
	sales_invoice_data = get_sales_invoice_data(filters)
	data = []
	for inv in sales_invoice_data:
		row = [inv.posting_date, inv.owner, inv.mode_of_payment,inv.warehouse,
			inv.cost_center,inv.net_total, inv.total_taxes, inv.paid_amount,
			(inv.net_total + inv.total_taxes - inv.paid_amount)]
		data.append(row)
	return data

def get_conditions(filters):
	conditions = ""
	if filters.get("company"): conditions += " a.company=%(company)s"
	if filters.get("customer"): conditions += " and a.customer = %(customer)s"
	if filters.get("owner"): conditions += " and a.owner = %(owner)s"
	if filters.get("from_date"): conditions += " and a.posting_date >= %(from_date)s"
	if filters.get("to_date"): conditions += " and a.posting_date <= %(to_date)s"
	if filters.get("mode_of_payment"): conditions += " and c.mode_of_payment >= %(mode_of_payment)s"
	if filters.get("warehouse"): conditions += " and b.warehouse <= %(warehouse)s"
	if filters.get("cost_center"): conditions += " and b.cost_center <= %(cost_center)s"
	if filters.get("is_pos"): conditions += " and a.is_pos = %(is_pos)s"

	return conditions

def get_sales_invoice_data(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select
			a.owner, a.posting_date, c.mode_of_payment, b.warehouse, b.cost_center,
			sum(a.net_total) as "net_total",
			sum(a.total_taxes_and_charges) as "total_taxes",
			sum(a.base_paid_amount) as "paid_amount"
		from `tabSales Invoice` a, `tabSales Invoice Item` b, `tabSales Invoice Payment` c
		where
			a.name = b.parent
			and a.name = c.parent
			and {conditions}
			group by
			a.owner, a.posting_date, c.mode_of_payment, b.warehouse, b.cost_center
	""".format(conditions=conditions), filters, as_dict=1)