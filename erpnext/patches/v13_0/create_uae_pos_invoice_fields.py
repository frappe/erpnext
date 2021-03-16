# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from erpnext.regional.united_arab_emirates.setup import make_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': ['in', ['Saudi Arabia', 'United Arab Emirates']]})
	if not company:
		return

	make_custom_fields()