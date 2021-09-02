from __future__ import unicode_literals

import frappe

from erpnext.setup.setup_wizard.operations.install_fixtures import add_market_segments


def execute():
	frappe.reload_doc('crm', 'doctype', 'market_segment')

	frappe.local.lang = frappe.db.get_default("lang") or 'en'

	add_market_segments()
