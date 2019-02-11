from __future__ import unicode_literals
import frappe

def execute():
	for doctype in ('Sales Order', 'Purchase Order', 'Sales Invoice',
		'Purchase Invoice'):
		frappe.reload_doctype(doctype)
		frappe.db.sql('''update `tab{0}` set submit_on_creation=1, notify_by_email=1
			where is_recurring=1'''.format(doctype))
		frappe.db.sql('''update `tab{0}` set notify_by_email=1
			where is_recurring=1'''.format(doctype))
		frappe.db.sql('''update `tab{0}` set recurring_id = name
			where is_recurring=1 and ifnull(recurring_id, '') = "" '''.format(doctype))
