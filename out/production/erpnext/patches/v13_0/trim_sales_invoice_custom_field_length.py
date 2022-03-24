# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.regional.india.setup import create_custom_fields, get_custom_fields


def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	custom_fields = {
		'Sales Invoice': get_custom_fields().get('Sales Invoice')
	}

	create_custom_fields(custom_fields, update=True)
