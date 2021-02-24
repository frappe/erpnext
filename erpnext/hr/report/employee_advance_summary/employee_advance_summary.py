# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.utils import flt
from erpnext.accounts.utils import get_currency_precision
from erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment import get_employee_currency

def execute(filters=None):
	if not filters: filters = {}

	advances = get_advances(filters)
	columns = get_columns()

	if not advances:
		msgprint(_("No record found"))
		return columns, advances

	data = get_data(advances, filters)

	return columns, data


def get_columns():
	return [
		{
			"label": _("Title"),
			"fieldname": "title",
			"fieldtype": "Link",
			"options": "Employee Advance",
			"width": 120
		},
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 120
		},
		{
			"label": _("Advance Amount"),
			"fieldname": "advance_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"label": _("Paid Amount"),
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"label": _("Claimed Amount"),
			"fieldname": "claimed_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 120
		}
	]

def get_conditions(filters):
	conditions = {}

	if filters.get("employee"):
		conditions["employee"] = filters.employee

	if filters.get("company"):
		conditions["company"] = filters.company

	if filters.get("status"):
		conditions["status"] = filters.status

	if filters.get("from_date"):
		conditions["posting_date"] = (">=", filters.from_date)

	if filters.get("to_date"):
		conditions["posting_date"] = ("<=", filters.to_date)

	return conditions

def get_advances(filters):
	conditions = get_conditions(filters)
	conditions["docstatus"] = ("<", 2)

	return frappe.db.get_list("Employee Advance",
		fields = ["name", "employee", "paid_amount", "status", "advance_amount",
			"claimed_amount", "company", "posting_date", "purpose", "exchange_rate"],
		filters = conditions,
		order_by = "posting_date, name desc"
	)

def get_data(advances, filters):
	currency_precision = get_currency_precision() or 2
	company_currency = frappe.get_cached_value("Company", filters.get("company"), "default_currency")

	for adv in advances:
		employee_currency = get_employee_currency(adv.employee)

		# if employee filter is applied show the report in employee currency, else in company currency

		if filters.get("employee"):
			adv.currency = employee_currency
		else:
			adv.currency = company_currency

		if filters.get("employee") and adv.currency == employee_currency:
			adv["paid_amount"] = adv.paid_amount
			adv["advance_amount"] = adv.advance_amount
			adv["claimed_amount"] = adv.claimed_amount
		else:
			adv["paid_amount"] = flt(flt(adv.paid_amount) *
				flt(adv.exchange_rate), currency_precision)

			adv["advance_amount"] = flt(flt(adv.advance_amount) *
				flt(adv.exchange_rate), currency_precision)

			adv["claimed_amount"] = flt(flt(adv.claimed_amount) *
				flt(adv.exchange_rate), currency_precision)

	return advances