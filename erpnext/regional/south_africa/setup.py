# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission, update_permission_property

def setup(company=None, patch=True):
	make_custom_fields()
	add_permissions()

def make_custom_fields(update=True):
	is_zero_rated = dict(fieldname='is_zero_rated', label='Is Zero Rated',
		fieldtype='Check', fetch_from='item_code.is_zero_rated',
		insert_after='description', print_hide=1)
	custom_fields = {
		'Item': [
			dict(fieldname='is_zero_rated', label='Is Zero Rated',
				fieldtype='Check', insert_after='item_group',
				print_hide=1)
		],
		'Sales Invoice Item': is_zero_rated,
		'Purchase Invoice Item': is_zero_rated
	}

	create_custom_fields(custom_fields, update=update)

def add_permissions():
	"""Add Permissions for South Africa VAT Settings and South Africa VAT Account
		and VAT Audit Report"""
	for doctype in ('South Africa VAT Settings', 'South Africa VAT Account'):
		add_permission(doctype, 'All', 0)
		for role in ('Accounts Manager', 'Accounts User', 'System Manager'):
			add_permission(doctype, role, 0)
			update_permission_property(doctype, role, 0, 'write', 1)
			update_permission_property(doctype, role, 0, 'create', 1)


	if not frappe.db.get_value('Custom Role', dict(report="VAT Audit Report")):
		frappe.get_doc(dict(
			doctype='Custom Role',
			report="VAT Audit Report",
			roles= [
				dict(role='Accounts User'),
				dict(role='Accounts Manager'),
				dict(role='Auditor')
			]
		)).insert()
