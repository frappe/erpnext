# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	
	columns = [_("FTI Document") + "::240",_("FTI Date Of Issue") + "::240", _("Discount Reason",) + "::240", _("Total Discount") + ":Currency:120", _("Invoice Total") + ":Currency:120", _("Discount Rate") + "::240", _("Users") + "::240"]
	
	data = return_data(filters)

	return columns, data

def return_data(filters):
	data = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)
	salary_slips = frappe.get_all("Sales Invoice", ["name", "naming_series", "posting_date", "grand_total", "discount_reason", "discount_amount", "additional_discount_percentage", "cashier"], filters = conditions,  order_by = "name asc")

	for salary in salary_slips:
		additional_discount_percentage = int(float(salary.additional_discount_percentage))
		fti_document = salary.name
		fti_date = salary.posting_date
		discount_reason = salary.discount_reason
		total_discount = salary.discount_amount
		invoice_total = salary.grand_total
		discount_rate = "{}%".format(additional_discount_percentage)
		user = salary.cashier

		row = [fti_document, fti_date, discount_reason, total_discount, invoice_total, discount_rate, user]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"creation_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "discount_amount": [">", 0]'
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += '}'

	return conditions