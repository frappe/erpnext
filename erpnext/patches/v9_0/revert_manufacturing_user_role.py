from __future__ import unicode_literals
import frappe

def execute():
	if 'Manufacturing' in frappe.get_active_domains(): return

	role = 'Manufacturing User'
	frappe.db.set_value('Role', role, 'restrict_to_domain', '')
	frappe.db.set_value('Role', role, 'disabled', 0)

	users = frappe.get_all('Has Role', filters = {
		'parenttype': 'User',
		'role': ('in', ['System Manager', 'Manufacturing Manager'])
	}, fields=['parent'], as_list=1)

	for user in users:
		_user = frappe.get_doc('User', user[0])
		_user.append('roles', {
			'role': role
		})
		_user.flags.ignore_validate = True
		_user.save()
