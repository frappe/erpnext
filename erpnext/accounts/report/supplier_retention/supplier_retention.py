# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Name") + "::240", _("Date") + "::240", _("Supplier") + "::240", _("Supplier RTN") + "::240", _("CAI") + "::240", _("Due Date") + "::240"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	groups = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	retentions = frappe.get_all("Supplier Retention", ["*"], filters = conditions)
	
	for retention in retentions:
		row = [retention.name, retention.posting_date, retention.supplier, retention.rtn, retention.cai, retention.due_date]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += ', "supplier": "{}"'.format(filters.get("supplier"))
	conditions += '}'

	return conditions