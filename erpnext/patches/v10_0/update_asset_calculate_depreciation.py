from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('assets', 'doctype', 'asset')
	frappe.reload_doc('assets', 'doctype', 'depreciation_schedule')

	frappe.db.sql("""
		update tabAsset a
		set calculate_depreciation = 1
		where exists(select ds.name from `tabDepreciation Schedule` ds where ds.parent=a.name)
	""")