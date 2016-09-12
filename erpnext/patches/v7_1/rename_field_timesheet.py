from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	doctype = 'Timesheet'
	if "total_billing_amount" in frappe.db.get_table_columns(doctype):
		rename_field(doctype, 'total_billing_amount', 'total_billable_amount')