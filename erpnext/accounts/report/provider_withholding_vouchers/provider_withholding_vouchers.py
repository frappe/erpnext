# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
import datetime

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Supplier Retention") + "::240", _("Date") + "::240", _("Supplier") + "::240", _("RTN") + "::240", _("CAI") + "::240", _("Due Date") + "::240", _("% Retention") + "::240", _("Type Document") + "::240", _("Document") + "::240", _("Base") + ":Currency:120", _("Amount") + ":Currency:120"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	dates = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	retentions = frappe.get_all("Supplier Retention", ["*"], filters = conditions)

	for retention in retentions:
		references = frappe.get_all("Withholding Reference", ["*"], filters = {"parent": retention.name})

		for reference in references:
			percentage_str = str(retention.percentage_total)
			percentage = "{}%".format(percentage_str)
			amount = reference.net_total * (retention.percentage_total/100) 
			row = [retention.name, retention.posting_date, retention.supplier, retention.rtn, retention.cai, retention.due_date, percentage, reference.reference_doctype, reference.reference_name, reference.net_total, amount]
			data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += '}'

	return conditions