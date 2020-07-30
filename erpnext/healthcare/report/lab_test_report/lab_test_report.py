# Copyright (c) 2016, ESS
# License: See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}

	data, columns = [], []

	columns = get_columns()
	lab_test_list = get_lab_tests(filters)

	if not lab_test_list:
		msgprint(_("No records found"))
		return columns, lab_test_list

	data = []
	for lab_test in lab_test_list:
		row = frappe._dict({
				'test': lab_test.name,
				'template': lab_test.template,
				'company': lab_test.company,
				'patient': lab_test.patient,
				'patient_name': lab_test.patient_name,
				'practitioner': lab_test.practitioner,
				'employee': lab_test.employee,
				'status': lab_test.status,
				'invoiced': lab_test.invoiced,
				'result_date': lab_test.result_date,
				'department': lab_test.department
			})
		data.append(row)

	return columns, data


def get_columns():
	return [
		{
			"fieldname": "test",
			"label": _("Lab Test"),
			"fieldtype": "Link",
			"options": "Lab Test",
			"width": "120"
		},
		{
			"fieldname": "template",
			"label": _("Lab Test Template"),
			"fieldtype": "Link",
			"options": "Lab Test Template",
			"width": "120"
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": "120"
		},
		{
			"fieldname": "patient",
			"label": _("Patient"),
			"fieldtype": "Link",
			"options": "Patient",
			"width": "120"
		},
		{
			"fieldname": "patient_name",
			"label": _("Patient Name"),
			"fieldtype": "Data",
			"width": "120"
		},
		{
			"fieldname": "practitioner",
			"label": _("Requesting Practitioner"),
			"fieldtype": "Link",
			"options": "Healthcare Practitioner",
			"width": "120"
		},
		{
			"fieldname": "employee",
			"label": _("Lab Technician"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": "120"
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": "100"
		},
		{
			"fieldname": "invoiced",
			"label": _("Invoiced"),
			"fieldtype": "Check",
			"width": "100"
		},
		{
			"fieldname": "result_date",
			"label": _("Result Date"),
			"fieldtype": "Date",
			"width": "100"
		},
		{
			"fieldname": "department",
			"label": _("Medical Department"),
			"fieldtype": "Link",
			"options": "Medical Department",
			"width": "100"
		}
	]

def get_lab_tests(filters):
	conditions = get_conditions(filters)
	data = frappe.get_all(
		doctype='Lab Test',
		fields=['name', 'template', 'company', 'patient', 'patient_name', 'practitioner', 'employee', 'status', 'invoiced', 'result_date', 'department'],
		filters=conditions,
		order_by='submitted_date desc'
	)
	return data

def get_conditions(filters):
	conditions = {
		'docstatus': ('=', 1)
	}

	if filters.get('from_date') and filters.get('to_date'):
		conditions['result_date'] = ('between', (filters.get('from_date'), filters.get('to_date')))
		filters.pop('from_date')
		filters.pop('to_date')

	for key, value in filters.items():
		if filters.get(key):
			conditions[key] = value

	return conditions