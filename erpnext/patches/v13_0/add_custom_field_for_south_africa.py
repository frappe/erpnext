# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.regional.south_africa.setup import add_permissions, make_custom_fields


def execute():
	company = frappe.get_all('Company', filters = {'country': 'South Africa'})
	if not company:
		return

	frappe.reload_doc('regional', 'doctype', 'south_africa_vat_settings')
	frappe.reload_doc('regional', 'report', 'vat_audit_report')
	frappe.reload_doc('accounts', 'doctype', 'south_africa_vat_account')

	make_custom_fields()
	add_permissions()
