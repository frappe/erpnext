import frappe
from frappe import _
from erpnext.setup.setup_wizard.operations.install_fixtures import make_fixture_records

def execute():
	frappe.reload_doc('crm', 'doctype', 'sales_stage')

	frappe.local.lang = frappe.db.get_default("lang") or 'en'

	records = [
		{"doctype": "Sales Stage", "stage_name": _("Prospecting")},
		{"doctype": "Sales Stage", "stage_name": _("Qualification")},
		{"doctype": "Sales Stage", "stage_name": _("Needs Analysis")},
		{"doctype": "Sales Stage", "stage_name": _("Value Proposition")},
		{"doctype": "Sales Stage", "stage_name": _("Identifying Decision Makers")},
		{"doctype": "Sales Stage", "stage_name": _("Perception Analysis")},
		{"doctype": "Sales Stage", "stage_name": _("Proposal/Price Quote")},
		{"doctype": "Sales Stage", "stage_name": _("Negotiation/Review")}
	]

	make_fixture_records(records)