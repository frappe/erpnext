import frappe
from frappe import _


def execute():
	"""assign lft and rgt appropriately"""
	if "Healthcare" not in frappe.get_active_domains():
		return

	frappe.reload_doc("healthcare", "doctype", "healthcare_service_unit")
	frappe.reload_doc("healthcare", "doctype", "healthcare_service_unit_type")
	company = frappe.get_value("Company", {"domain": "Healthcare"}, "name")

	if company:
		frappe.get_doc(
			{
				"doctype": "Healthcare Service Unit",
				"healthcare_service_unit_name": _("All Healthcare Service Units"),
				"is_group": 1,
				"company": company,
			}
		).insert(ignore_permissions=True)
