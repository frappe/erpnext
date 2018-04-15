# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class EmployeePromotion(Document):
	pass


@frappe.whitelist()
def get_employee_fields_label():
	fields = []
	for df in frappe.get_meta("Employee").get("fields"):
		if df.fieldtype in ["Data", "Date", "Datetime", "Float", "Int"
		"Link", "Long Text", "Percent", "Select", "Small Text", "Text"]:
			fields.append({"value": df.fieldname, "label": df.label})
	return fields
