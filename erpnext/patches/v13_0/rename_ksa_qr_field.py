# Copyright (c) 2020, Wahni Green Technologies and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	company = frappe.get_all('Company', filters = {'country': 'Saudi Arabia'})
	if not company:
		return

	if frappe.db.exists('DocType', 'Sales Invoice'):
		frappe.reload_doc('accounts', 'doctype', 'sales_invoice', force=True)
		if frappe.db.has_column('Sales Invoice', 'qr_code'):
			rename_field('Sales Invoice', 'qr_code', 'ksa_einv_qr')
