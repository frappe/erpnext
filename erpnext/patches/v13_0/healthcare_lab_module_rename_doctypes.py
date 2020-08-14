from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	if frappe.db.exists('DocType', 'Lab Test') and frappe.db.exists('DocType', 'Lab Test Template'):
		# rename child doctypes
		doctypes = {
			'Lab Test Groups': 'Lab Test Group Template',
			'Normal Test Items': 'Normal Test Result',
			'Sensitivity Test Items': 'Sensitivity Test Result',
			'Special Test Items': 'Descriptive Test Result',
			'Special Test Template': 'Descriptive Test Template'
		}

		frappe.reload_doc('healthcare', 'doctype', 'lab_test')
		frappe.reload_doc('healthcare', 'doctype', 'lab_test_template')

		for old_dt, new_dt in doctypes.items():
			if not frappe.db.table_exists(new_dt) and frappe.db.table_exists(old_dt):
				frappe.rename_doc('DocType', old_dt, new_dt, force=True)
				frappe.reload_doc('healthcare', 'doctype', frappe.scrub(new_dt))
				frappe.delete_doc_if_exists('DocType', old_dt)

		parent_fields = {
			'Lab Test Group Template': 'lab_test_groups',
			'Descriptive Test Template': 'descriptive_test_templates',
			'Normal Test Result': 'normal_test_items',
			'Sensitivity Test Result': 'sensitivity_test_items',
			'Descriptive Test Result': 'descriptive_test_items'
		}

		for doctype, parentfield in parent_fields.items():
			frappe.db.sql("""
				UPDATE `tab{0}`
				SET parentfield = %(parentfield)s
			""".format(doctype), {'parentfield': parentfield})

		# rename field
		frappe.reload_doc('healthcare', 'doctype', 'lab_test')
		if frappe.db.has_column('Lab Test', 'special_toggle'):
			rename_field('Lab Test', 'special_toggle', 'descriptive_toggle')

	if frappe.db.exists('DocType', 'Lab Test Group Template'):
		# fix select field option
		frappe.reload_doc('healthcare', 'doctype', 'lab_test_group_template')
		frappe.db.sql("""
			UPDATE `tabLab Test Group Template`
			SET template_or_new_line = 'Add New Line'
			WHERE template_or_new_line = 'Add new line'
		""")
