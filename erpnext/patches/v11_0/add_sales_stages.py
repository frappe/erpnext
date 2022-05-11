import frappe

from erpnext.setup.setup_wizard.operations.install_fixtures import add_sale_stages


def execute():
	frappe.reload_doc("crm", "doctype", "sales_stage")

	frappe.local.lang = frappe.db.get_default("lang") or "en"

	add_sale_stages()
