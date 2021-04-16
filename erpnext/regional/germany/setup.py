import os
import frappe


def setup(company=None, patch=True):
	add_custom_roles_for_reports()


def add_custom_roles_for_reports():
	"""Add Access Control to UAE VAT 201."""
	if not frappe.db.get_value('Custom Role', dict(report='DATEV')):
		frappe.get_doc(dict(
			doctype='Custom Role',
			report='DATEV',
			roles= [
				dict(role='Accounts User'),
				dict(role='Accounts Manager')
			]
		)).insert()