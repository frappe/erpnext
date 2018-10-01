
import frappe
from frappe import _
from erpnext.setup.setup_wizard.operations.install_fixtures import make_fixture_records

def execute():
	frappe.reload_doc('crm', 'doctype', 'market_segment')

	frappe.local.lang = frappe.db.get_default("lang") or 'en'

	records = [
		{"doctype": "Market Segment", "market_segment": _("Lower Income")},
		{"doctype": "Market Segment", "market_segment": _("Middle Income")},
		{"doctype": "Market Segment", "market_segment": _("Upper Income")}
	]

	make_fixture_records(records)