from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype('Role')
	frappe.reload_doctype('User')
	for role_name in ('Customer', 'Supplier', 'Student'):
		if frappe.db.exists('Role', role_name):
			frappe.db.set_value('Role', role_name, 'desk_access', 0)
		else:
			frappe.get_doc(dict(doctype='Role', role_name=role_name, desk_access=0)).insert()


	# set customer, supplier roles
	for c in frappe.get_all('Contact', fields=['user'], filters={'ifnull(user, "")': ('!=', '')}):
		user = frappe.get_doc('User', c.user)
		user.flags.ignore_validate = True
		user.flags.ignore_mandatory = True
		user.save()


