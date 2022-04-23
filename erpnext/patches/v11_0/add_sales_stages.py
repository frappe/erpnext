from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.setup.setup_wizard.operations.install_fixtures import add_sale_stages

def execute():
	frappe.reload_doc('crm', 'doctype', 'sales_stage')

	frappe.local.lang = frappe.db.get_default("lang") or 'en'

	add_sale_stages()