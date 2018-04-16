# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def set_employee_name(doc):
	if doc.employee and not doc.employee_name:
		doc.employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")


@frappe.whitelist()
def get_employee_fields_label():
	fields = []
	for df in frappe.get_meta("Employee").get("fields"):
		if df.fieldtype in ["Data", "Date", "Datetime", "Float", "Int"
		"Link", "Long Text", "Percent", "Select", "Small Text", "Text"]:
			fields.append({"value": df.fieldname, "label": df.label})
	return fields
