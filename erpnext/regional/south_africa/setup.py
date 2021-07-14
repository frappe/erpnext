# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, os, json
from frappe.permissions import add_permission, update_permission_property

def setup():
	add_permissions()

def add_permissions():
	"""Add Permissions for South Africa VAT Settings and South Africa VAT Account"""
	for doctype in ('South Africa VAT Settings', 'South Africa VAT Account'):
		add_permission(doctype, 'All', 0)
		for role in ('Accounts Manager', 'Accounts User', 'System Manager'):
			add_permission(doctype, role, 0)
			update_permission_property(doctype, role, 0, 'write', 1)
			update_permission_property(doctype, role, 0, 'create', 1)