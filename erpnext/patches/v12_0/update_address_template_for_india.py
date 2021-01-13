# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.regional.address_template.setup import set_up_address_templates

def execute():
	if frappe.db.get_value('Company',  {'country': 'India'},  'name'):
		address_template = frappe.db.get_value('Address Template', 'India', 'template')
		if not address_template or "gstin" not in address_template:
			set_up_address_templates(default_country='India')
