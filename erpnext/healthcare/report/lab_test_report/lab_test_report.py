# Copyright (c) 2016, ESS
# License: See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}

	lab_test_list = get_lab_test(filters)
	columns = get_columns()

	if not lab_test_list:
		msgprint(_("No record found"))
		return columns, lab_test_list

	data = []
	for lab_test in lab_test_list:
		row = [ lab_test.lab_test_name, lab_test.patient, lab_test.practitioner, lab_test.invoiced, lab_test.status, lab_test.result_date, lab_test.department]
		data.append(row)

	return columns, data


def get_columns():
	columns = [
		_("Test") + ":Data:120",
		_("Patient") + ":Link/Patient:180",
		_("Healthcare Practitioner") + ":Link/Healthcare Practitioner:120",
		_("Invoiced") + ":Check:100",
		_("Status") + ":Data:120",
		_("Result Date") + ":Date:120",
		_("Department") + ":Data:120",
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
	if filters.get("department"):
		conditions += " and department = %(department)s"

	return conditions

def get_lab_test(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select name, patient, lab_test_name, patient_name, status, result_date, practitioner, invoiced, department
		from `tabLab Test`
		where docstatus<2 %s order by submitted_date desc, name desc""" %
		conditions, filters, as_dict=1)
