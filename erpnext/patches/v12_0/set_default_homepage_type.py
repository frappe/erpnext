import frappe


def execute():
	frappe.db.set_single_value("Homepage", "hero_section_based_on", "Default")
