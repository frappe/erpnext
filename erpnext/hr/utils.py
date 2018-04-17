# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, format_datetime

def set_employee_name(doc):
	if doc.employee and not doc.employee_name:
		doc.employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")

@frappe.whitelist()
def get_employee_fields_label():
	fields = []
	for df in frappe.get_meta("Employee").get("fields"):
		if df.fieldtype in ["Data", "Date", "Datetime", "Float", "Int",
		"Link", "Percent", "Select", "Small Text"]:
			fields.append({"value": df.fieldname, "label": df.label})
	return fields

@frappe.whitelist()
def get_employee_field_property(employee, fieldname):
	if employee and fieldname:
		field = frappe.get_meta("Employee").get_field(fieldname)
		value = frappe.db.get_value("Employee", employee, fieldname)
		options = None
		if field.fieldtype in ["Link", "Select"]:
			options = field.options
		if field.fieldtype == "Date":
			value = formatdate(value)
		elif field.fieldtype == "Datetime":
			value = format_datetime(value)
		return {
			"value" : value,
			"datatype" : field.fieldtype,
			"options" : options
		}
	else:
		return False
