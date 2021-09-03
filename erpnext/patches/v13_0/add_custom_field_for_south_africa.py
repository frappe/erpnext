# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

<<<<<<< HEAD
from __future__ import unicode_literals
=======
>>>>>>> d1fe060e4a (fix: south africa vat patch failure (#27323))
import frappe
from erpnext.regional.south_africa.setup import make_custom_fields, add_permissions

def execute():
	company = frappe.get_all('Company', filters = {'country': 'South Africa'})
	if not company:
		return

	frappe.reload_doc('regional', 'doctype', 'south_africa_vat_settings')
	frappe.reload_doc('accounts', 'doctype', 'south_africa_vat_account')

	make_custom_fields()
	add_permissions()
