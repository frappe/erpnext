from __future__ import unicode_literals
import frappe

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	if frappe.db.exists('Report', 'E-Invoice Summary') and \
		not frappe.db.get_value('Custom Role', dict(report='E-Invoice Summary')):
		frappe.get_doc(dict(
			doctype='Custom Role',
			report='E-Invoice Summary',
			roles= [
				dict(role='Accounts User'),
				dict(role='Accounts Manager')
			]
		)).insert()	