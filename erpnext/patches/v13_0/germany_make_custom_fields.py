# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from erpnext.regional.germany.setup import make_custom_fields

def execute():
	company_list = frappe.get_all('Company', filters = {'country': 'Germany'})
	if not company_list:
		return

	make_custom_fields()
