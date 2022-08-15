# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from dateutil import parser

def execute(filters=None):
	filters = frappe._dict(filters or {})
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

	columns = get_columns(filters)
	data = get_data(filters)
	print(data)

	return columns, data

def get_columns(filters):
	return [
		{"label": _("Patient Name"), "fieldtype": "Data", "fieldname": "patient_name", "width": 140},
		{
			"label": _("Gender"), 
			"fieldtype": "Link", 
			"fieldname": "sex",
			"options": "Gender", 
			"width": 100
		},
		{
			"label": _("Medical Department"), 
			"fieldtype": "Link", 
			"fieldname": "medical_department", 
			"options": "Medical Department",
			"width": 150
		},
		{
			"label": _("Blood Group"), 
			"fieldtype": "Select", 
			"fieldname": "blood_group", 
			"width": 100
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Select", "width": 100},
		{"label": _("Phone"), "fieldname": "phone", "fieldtype": "data", "width": 120},
		{"label": _("Email"), "fieldname": "email", "fieldtype": "data", "width": 150},
	]

def get_data(filters):

	data = []
	department = filters.get("medical_department")
	patients_data = get_patients_details(department)
	filter_from_date = parser.parse(filters.from_date)
	filter_to_date = parser.parse(filters.to_date)
	if patients_data:
		for pd in patients_data:
			if filter_from_date.date() <= pd.creation.date() and pd.creation.date() <= filter_to_date.date():
				row = {
					"patient_name": pd.get("patient_name"),
					"gender": pd.get("sex"),
					"medical_department":pd.get("medical_department"),
					"blood_group":pd.get("blood_group"),
					"status":pd.get("status"),
					"phone":pd.get("phone"),
					"email":pd.get("email")
				}
				data.append(row)

	return data


def get_patients_details(department):
	values = {'department': department}
	if department:
		return frappe.db.sql(
			"""
			SELECT
				patient_name, sex, medical_department,
				blood_group,status,phone,email
				creation
			FROM
				`tabPatient`
			WHERE
				medical_department = %(department)s
		""",
			values=values,
			as_dict=1,
		)
	else:
		return frappe.db.sql(
			"""
			SELECT
				patient_name, sex, medical_department,
				blood_group,status,phone,
				creation
			FROM
				`tabPatient`
		""",
			as_dict=1,
		)