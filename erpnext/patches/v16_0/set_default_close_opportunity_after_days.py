import frappe


def execute():
	"""Backfill the default for CRM Settings.close_opportunity_after_days.

	The auto-close logic used to fall back to 15 days in code. Now that the fallback is removed,
	existing sites that never set the value (left blank / 0) need it filled in so opportunities
	keep auto-closing on the same schedule.
	"""
	if not frappe.db.get_single_value("CRM Settings", "close_opportunity_after_days"):
		frappe.db.set_single_value("CRM Settings", "close_opportunity_after_days", 15)
