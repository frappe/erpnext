from __future__ import unicode_literals
import frappe

def execute():
	# Rename fields
	frappe.reload_doc('healthcare', 'doctype', frappe.scrub('Lab Test Template'))
	if frappe.db.has_column('Lab Test Template', 'special_test_template'):
		rename_field('Lab Test Template', 'special_test_template', 'descriptive_test_templates')

	frappe.reload_doc('healthcare', 'doctype', frappe.scrub('Lab Test'))
	if frappe.db.has_column('Lab Test', 'special_test_items'):
		rename_field('Lab Test', 'special_test_items', 'descriptive_test_items')

	# Rename doctypes
	doctypes = {
		'Lab Test Groups': 'Lab Test Group Template',
		'Special Test Template': 'Descriptive Test Template',
		'Normal Test Items': 'Normal Test Result',
		'Special Test Items': 'Descriptive Test Result',
		'Organism Test Item': 'Organism Test Result',
		'Sensitivity Test Items': 'Sensitivity Test Result'
	}

	for old_dt, new_dt in doctypes.items():
		if not frappe.db.table_exists(new_dt) and frappe.db.table_exists(old_dt):
			frappe.reload_doc("healthcare", "doctype", frappe.scrub(old_dt))
			frappe.rename_doc('DocType', old_dt, new_dt)
			frappe.reload_doc("healthcare", "doctype", frappe.scrub(new_dt))
			frappe.delete_doc("DocType", old_dt)
