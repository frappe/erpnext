from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	doctype = 'Timesheet'
	fields_dict = {'total_billing_amount': 'total_billable_amount', 'total_billing_hours': 'total_billable_hours'}

	for old_fieldname, new_fieldname in fields_dict.items():
		if old_fieldname in frappe.db.get_table_columns(doctype):
			rename_field(doctype, old_fieldname, new_fieldname)
