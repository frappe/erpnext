from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	if "billable" in frappe.db.get_table_columns("Timesheet Detail"):
		rename_field("Timesheet Detail", "billable", "is_billable")