# Copyright (c) 2016, ESS
# License: See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}

	lab_test_list = get_lab_test(filters)
	columns = get_columns()

	if not lab_test_list:
		msgprint(_("No record found"))
		return columns, lab_test_list

	data = []
	for lp in lab_test_list:
		status = "Draft"
		if(lp.docstatus == 1):
			status = "Submitted"
			if(lp.approval_status == "Approved"):
				status = "Approved"
		elif(lp.docstatus == 2):
			status = "Cancelled"
		row = [ lp.test_name, lp.patient, lp.physician, lp.invoice, status, lp.result_date, lp.lab_test_type]

		data.append(row)

	return columns, data


def get_columns():
	columns = [
		_("Test") + ":Data:120",
		_("Patient") + ":Link/Patient:180",
		_("Doctor") + ":Link/Physician:120",
		_("Invoice") + ":Link/Sales Invoice:120",
		_("Status") + ":Data:120",
		_("Result Date") + ":Date:120",
		_("Service Type") + ":Data:120",
	]

	return columns

def get_conditions(filters):
	conditions = ""

	if filters.get("patient"):
		conditions += "and patient = %(patient)s"
	if filters.get("from_date"):
		conditions += "and result_date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " and result_date <= %(to_date)s"
	if filters.get("lab_test_type"):
		conditions += " and lab_test_type = %(lab_test_type)s"

	return conditions

def get_lab_test(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select name, patient, test_name, patient_name, docstatus, 			result_date, physician, invoice, lab_test_type
		from `tabLab Test`
		where docstatus<2 %s order by submitted_date desc, name desc""" %
		conditions, filters, as_dict=1)
