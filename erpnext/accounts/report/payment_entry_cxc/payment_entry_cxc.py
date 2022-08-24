# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
import datetime

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Date") + "::240", _("Serie") + "::240", _("Status") + "::240", _("Type") + "::240", _("Name") + "::240", _("Customer") + "::240", _("Party RTN") + "::240", _("Company") + "::240", _("Reason Payment") + "::240",  _("Paid Amount") + ":Currency:120", _("Total Allocated Amount") + ":Currency:120",_("Unallocated Amount") + ":Currency:120",_("Difference Amount (Company Currency)") + ":Currency:120", _("Cheque/Reference No") + "::240", _("Cheque/Reference Date") + "::240", _("Created By") + "::240"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	registers = frappe.get_all("Payment Entry", ["*"], filters = conditions,  order_by = "name asc")

	for register in registers:
		references = frappe.get_all("Payment Entry Reference", ["*"], filters = {"parent": register.name})
		for refenrence in references:
			row = [register.posting_date, register.name, register.status, refenrence.reference_doctype, refenrence.reference_name, register.party_name, register.party_rtn, register.company, register.reason_payment, register.paid_amount, register.total_allocated_amount, register.unallocated_amount, register.difference_amount, register.reference_no, register.reference_date, register.user]
			data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"party_type": "Customer"'
	conditions += ', "posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	if filters.get("customer"): conditions += ', "party_name": "{}"'.format(filters.get("customer"))
	if filters.get("reason_payment"): conditions += ', "reason_payment": "{}"'.format(filters.get("reason_payment"))
	if filters.get("mode_of_payment"): conditions += ', "mode_of_payment": "{}"'.format(filters.get("mode_of_payment"))
	conditions += '}'

	return conditions