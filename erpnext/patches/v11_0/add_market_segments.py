
import frappe
from frappe import _
from erpnext.setup.setup_wizard.operations.install_fixtures import add_market_segments

def execute():
	frappe.reload_doc('crm', 'doctype', 'market_segment')

	frappe.local.lang = frappe.db.get_default("lang") or 'en'

	add_market_segments()