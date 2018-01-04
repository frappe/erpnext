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
	if frappe.db.exists("Doctype", "Guardian"):
		for user in frappe.db.sql_list("""select u.name from `tabUser` u , `tabGuardian` g where g.email_address = u.name"""):
			user = frappe.get_doc('User', user)
			user.flags.ignore_validate = True
			user.flags.ignore_mandatory = True
			user.save()
