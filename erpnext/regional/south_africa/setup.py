# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

# import frappe, os, json
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission, update_permission_property

def setup(company=None, patch=True):
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
	"""Add Permissions for South Africa VAT Settings and South Africa VAT Account"""
	for doctype in ('South Africa VAT Settings', 'South Africa VAT Account'):
		add_permission(doctype, 'All', 0)
		for role in ('Accounts Manager', 'Accounts User', 'System Manager'):
			add_permission(doctype, role, 0)
			update_permission_property(doctype, role, 0, 'write', 1)
			update_permission_property(doctype, role, 0, 'create', 1)