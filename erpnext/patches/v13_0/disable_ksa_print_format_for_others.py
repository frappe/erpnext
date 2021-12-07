# Copyright (c) 2020, Wahni Green Technologies and Contributors
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	company = frappe.get_all('Company', filters = {'country': 'Saudi Arabia'})
	if company:
		return

	if frappe.db.exists('DocType', 'Print Format'):
        frappe.db.sql("""UPDATE`tabPrint Format` SET disabled = 1 WHERE
    			name IN ('KSA VAT Invoice', 'KSA POS Invoice')""")
