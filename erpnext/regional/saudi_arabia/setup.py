# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.permissions import add_permission, update_permission_property
from erpnext.regional.united_arab_emirates.setup import make_custom_fields, add_print_formats
from erpnext.regional.saudi_arabia.wizard.operations.setup_ksa_vat_setting import create_ksa_vat_setting


def setup(company=None, patch=True):
	make_custom_fields()
	add_print_formats()
	add_permissions()
	create_ksa_vat_setting(company)
	

def add_permissions():
	"""Add Permissions for KSA VAT Setting."""
	add_permission('KSA VAT Setting', 'All', 0)
	for role in ('Accounts Manager', 'Accounts User', 'System Manager'):
		add_permission('KSA VAT Setting', role, 0)
		update_permission_property('KSA VAT Setting', role, 0, 'write', 1)
		update_permission_property('KSA VAT Setting', role, 0, 'create', 1)

	"""Enable KSA VAT Report"""
	frappe.db.set_value('Report', 'KSA VAT', 'disabled', 0)
