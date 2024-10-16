import frappe
from frappe.utils import cint


def execute():
	if cint(frappe.db.get_single_value("Accounts Settings", "calculate_depr_using_total_days")):
		frappe.db.set_single_value(
			"Accounts Settings", "calculate_daily_depreciation_using", "Total days in depreciation period"
		)
	else:
		frappe.db.set_single_value(
			"Accounts Settings", "calculate_daily_depreciation_using", "Total years in depreciation period"
		)
