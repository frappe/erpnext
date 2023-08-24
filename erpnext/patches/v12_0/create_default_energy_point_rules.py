import frappe

from erpnext.setup.install import create_default_energy_point_rules


def execute():
	frappe.reload_doc("social", "doctype", "energy_point_rule")
	create_default_energy_point_rules()
