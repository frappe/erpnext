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
	columns= [
		{
			"label": _("Loan Security Pledge"),
			"fieldtype": "Link",
			"fieldname": "loan_security_pledge",
			"options": "Loan Security Pledge",
			"width": 200
		},
		{
			"label": _("Loan"),
			"fieldtype": "Link",
			"fieldname": "loan",
			"options": "Loan",
			"width": 200
		},
		{
			"label": _("Applicant"),
			"fieldtype": "Data",
			"fieldname": "applicant",
			"width": 200
		},
		{
			"label": _("Status"),
			"fieldtype": "Data",
			"fieldname": "status",
			"width": 100
		},
		{
			"label": _("Pledge Time"),
			"fieldtype": "Data",
			"fieldname": "pledge_time",
			"width": 150
		},
		{
			"label": _("Loan Security"),
			"fieldtype": "Link",
			"fieldname": "loan_security",
			"options": "Loan Security",
			"width": 150
		},
		{
			"label": _("Quantity"),
			"fieldtype": "Float",
			"fieldname": "qty",
			"width": 100
		},
		{
			"label": _("Loan Security Price"),
			"fieldtype": "Currency",
			"fieldname": "loan_security_price",
			"options": "currency",
			"width": 200
		},
		{
			"label": _("Loan Security Value"),
			"fieldtype": "Currency",
			"fieldname": "loan_security_value",
			"options": "currency",
			"width": 200
		},
		{
			"label": _("Currency"),
			"fieldtype": "Link",
			"fieldname": "currency",
			"options": "Currency",
			"width": 50,
			"hidden": 1
		}
	]

	return columns

def get_data(filters):

	data = []
	conditions = get_conditions(filters)

	loan_security_pledges = frappe.db.sql("""
		SELECT
			p.name, p.applicant, p.loan, p.status, p.pledge_time,
			c.loan_security, c.qty, c.loan_security_price, c.amount
		FROM
			`tabLoan Security Pledge` p, `tabPledge` c
		WHERE
			p.docstatus = 1
			AND c.parent = p.name
			AND p.company = %(company)s
			{conditions}
	""".format(conditions = conditions), (filters), as_dict=1) #nosec

	default_currency = frappe.get_cached_value("Company", filters.get("company"), "default_currency")

	for pledge in loan_security_pledges:
		row = {}
		row["loan_security_pledge"] = pledge.name
		row["loan"] = pledge.loan
		row["applicant"] = pledge.applicant
		row["status"] = pledge.status
		row["pledge_time"] = pledge.pledge_time
		row["loan_security"] = pledge.loan_security
		row["qty"] = pledge.qty
		row["loan_security_price"] = pledge.loan_security_price
		row["loan_security_value"] = pledge.amount
		row["currency"] = default_currency

		data.append(row)

	return data

def get_conditions(filters):
	conditions = []

	if filters.get("applicant"):
		conditions.append("p.applicant = %(applicant)s")

	if filters.get("pledge_status"):
		conditions.append(" p.status = %(pledge_status)s")

	return "AND {}".format(" AND ".join(conditions)) if conditions else ""
