import frappe
from frappe.utils import cint


def execute():
	if not cint(frappe.db.get_single_value("Manufacturing Settings", "mins_between_operations")):
		frappe.db.set_single_value("Manufacturing Settings", "mins_between_operations", 10)
