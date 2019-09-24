import frappe

def execute():
	frappe.db.set_value('Homepage', 'Homepage', 'hero_section_based_on', 'Default')