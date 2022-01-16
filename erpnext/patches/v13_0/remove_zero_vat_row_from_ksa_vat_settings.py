# Copyright (c) 2022, Frappe Technologies and Contributors
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	company = frappe.get_all('Company', filters={'country': 'Saudi Arabia'})
	if not company:
		return

	selling = frappe.db.get_all('KSA VAT Sales Account', or_filters=[
		['title', '=', 'Zero rated domestic sales'],
		['title', '=', 'Exempted sales'],
	], pluck='name')

	for row in selling:
		frappe.delete_doc('KSA VAT Sales Account', row)

	buying = frappe.db.get_all('KSA VAT Purchase Account', or_filters=[
		['title', '=', 'Zero rated purchases'],
		['title', '=', 'Exempted purchases'],
	], pluck='name')

	for row in buying:
		frappe.delete_doc('KSA VAT Purchase Account', row)
