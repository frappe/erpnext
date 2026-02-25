import frappe


def execute():
	"""
	Description:
	Enable Legacy controller for Period Closing Voucher
	"""
	frappe.db.set_single_value("Accounts Settings", "use_legacy_controller_for_pcv", 1)
