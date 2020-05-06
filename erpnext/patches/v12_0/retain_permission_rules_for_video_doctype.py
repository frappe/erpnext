from __future__ import unicode_literals
import frappe

def execute():
	# to retain the roles and permissions from Education Module
	# after moving doctype to core
	permissions = frappe.db.sql("""
		SELECT
			*
		FROM
			`tabDocPerm`
		WHERE
			parent='Video'
	""", as_dict=True)

	frappe.reload_doc('core', 'doctype', 'video')
	doc = frappe.get_doc('DocType', 'Video')
	doc.permissions = []
	for perm in permissions:
		doc.append('permissions', perm)
	doc.save()
