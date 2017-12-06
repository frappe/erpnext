# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	# create guardian role
	if not frappe.get_value('Role', dict(role_name='Guardian')):
		frappe.get_doc({
			'doctype': 'Role',
			'role_name': 'Guardian',
			'desk_access': 0,
			'restrict_to_domain': 'Education'
		}).insert(ignore_permissions=True)
	
	# set guardian roles in already created users
	for g in frappe.get_all('Guardian', fields=['email_address'], filters={'ifnull(email_address, "")': ('!=', '')}):
		user = frappe.get_doc('User', g.email_address)
		user.flags.ignore_validate = True
		user.flags.ignore_mandatory = True
		user.save()
