from __future__ import unicode_literals

import frappe


def execute():
	frappe.db.sql("""
		update `tabMaterial Request`
		set status='Manufactured'
		where docstatus=1 and material_request_type='Manufacture' and per_ordered=100 and status != 'Stopped'
	""")
