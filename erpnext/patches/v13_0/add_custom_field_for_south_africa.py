# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.regional.south_africa.setup import make_custom_fields, add_permissions

def execute():
	company = frappe.get_all('Company', filters = {'country': 'South Africa'})
	if not company:
		return

	make_custom_fields()
	add_permissions()
