# Copyright (c) 2022, Frappe Technologies and Contributors
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	company = frappe.get_all('Company', filters={'country': 'Saudi Arabia'})
	if not company:
		return

	from erpnext.regional.saudi_arabia.wizard.operations.setup_ksa_vat_setting import (
		create_ksa_vat_setting,
	)
	frappe.reload_doc('regional', 'doctype', 'ksa_vat_setting')

	settings = frappe.db.get_all('KSA VAT Setting', pluck='name')
	for row in settings:
		frappe.delete_doc('KSA VAT Setting', row)
		create_ksa_vat_setting(row)
