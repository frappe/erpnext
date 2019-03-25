# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns = [
		{
			"label": _("Payroll Number"),
			"fieldtype": "Data",
			"fieldname": "payroll_no",
			"width": 150
		},
		{
			"label": _("Debit A/C Number"),
			"fieldtype": "Int",
			"fieldname": "Debit_account",
			"hidden": 1,
			"width": 200
		},
		{
			"label": _("Payment Date"),
			"fieldtype": "data",
			"fieldname": "payment_date",
			"width": 100
		},
		{
			"label": _("Employee Name"),
			"fieldtype": "data",
			"fieldname": "employee_name",
			"width": 200
		},
		{
			"label": _("Employee A/C Number"),
			"fieldtype": "Int",
			"fieldname": "employee_account_no",
			"width": 50
		},
		{
			"label": _("Bank Code"),
			"fieldtype": "data",
			"fieldname": "bank_code",
			"width": 100
		},
		{
			"label": _("Currency"),
			"fieldtype": "data",
			"fieldname": "currency",
			"width": 50
		},
		{
			"label": _("Net Salary Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"fieldname": "amount",
			"width": 100
		}
	]
	data = get_report_data(filters)

	return columns, data


def get_report_data(filters):
	data = []
	entries = frappe.get_all("Payroll Entry", fields=[" * "] )
	for entry in entries:
		employee_details = frappe.get_list(
		"Payroll Employee Detail",
		filters = {"parent": entry.name},
		fields=["*"]
		)
		for details in employee_details:
			payment_date = frappe.db.get_value("Salary Slip", {
				"payroll_entry": entry.name,
				"Employee": details.employee
			}, "modified")
			row = {
				"payroll_no": entry.name,
				"payment_date": frappe.utils.formatdate(payment_date.strftime('%Y-%m-%d')),
				"employee_account_no": frappe.db.get_value("Employee", details.employee, "bank_ac_no"),
				"bank_code": frappe.db.get_value("Employee", details.employee, "ifsc_code"),
				"employee_name": details.employee+": " + details.employee_name,
				"currency": frappe.get_cached_value('Company', filters.company,  'default_currency'),
				"amount": 100000000,
			}

			data.append(row)

	return data
