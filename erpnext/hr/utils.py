# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, format_datetime
from frappe.utils import getdate, get_datetime

def set_employee_name(doc):
	if doc.employee and not doc.employee_name:
		doc.employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")

@frappe.whitelist()
def get_employee_fields_label():
	fields = []
	for df in frappe.get_meta("Employee").get("fields"):
		if df.fieldtype in ["Data", "Date", "Datetime", "Float", "Int",
		"Link", "Percent", "Select", "Small Text"] and df.fieldname not in ["lft", "rgt", "old_parent"]:
			fields.append({"value": df.fieldname, "label": df.label})
	return fields

@frappe.whitelist()
def get_employee_field_property(employee, fieldname):
	if employee and fieldname:
		field = frappe.get_meta("Employee").get_field(fieldname)
		value = frappe.db.get_value("Employee", employee, fieldname)
		options = field.options
		if field.fieldtype == "Date":
			value = formatdate(value)
		elif field.fieldtype == "Datetime":
			value = format_datetime(value)
		return {
			"value" : value,
			"datatype" : field.fieldtype,
			"label" : field.label,
			"options" : options
		}
	else:
		return False

def update_employee(employee, details, cancel=False):
	for item in details:
		fieldtype = frappe.get_meta("Employee").get_field(item.fieldname).fieldtype
		new_data = item.new if not cancel else item.current
		if fieldtype == "Date" and new_data:
			new_data = getdate(new_data)
		elif fieldtype =="Datetime" and new_data:
			new_data = get_datetime(new_data)
		setattr(employee, item.fieldname, new_data)
	return employee

def validate_tax_declaration(declarations):
	subcategories = []
	for declaration in declarations:
		if declaration.exemption_sub_category in  subcategories:
			frappe.throw(_("More than one selection for {0} not \
			allowed").format(declaration.exemption_sub_category), frappe.ValidationError)
		subcategories.append(declaration.exemption_sub_category)
		max_amount = frappe.db.get_value("Employee Tax Exemption Sub Category", \
		declaration.exemption_sub_category, "max_amount")
		if declaration.amount > max_amount:
			frappe.throw(_("Max exemption amount for {0} is {1}").format(\
			declaration.exemption_sub_category, max_amount), frappe.ValidationError)
