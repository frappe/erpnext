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
			frappe.flags.link_fields = {}
			should_rename = (
				frappe.db.table_exists(old_dt)
				and not frappe.db.table_exists(new_dt)
			)
			if should_rename:
				frappe.reload_doc('healthcare', 'doctype', frappe.scrub(old_dt))
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

		# copy renamed child table fields (fields were already renamed in old doctype json, hence sql)
		rename_fields = {
			'lab_test_name': 'test_name',
			'lab_test_event': 'test_event',
			'lab_test_uom': 'test_uom',
			'lab_test_comment': 'test_comment'
		}

		for new, old in rename_fields.items():
			if frappe.db.has_column('Normal Test Result', old):
				frappe.db.sql("""UPDATE `tabNormal Test Result` SET {} = {}"""
					.format(new, old))

		if frappe.db.has_column('Normal Test Template', 'test_event'):
			frappe.db.sql("""UPDATE `tabNormal Test Template` SET lab_test_event = test_event""")

		if frappe.db.has_column('Normal Test Template', 'test_uom'):
			frappe.db.sql("""UPDATE `tabNormal Test Template` SET lab_test_uom = test_uom""")

		if frappe.db.has_column('Descriptive Test Result', 'test_particulars'):
			frappe.db.sql("""UPDATE `tabDescriptive Test Result` SET lab_test_particulars = test_particulars""")

		rename_fields = {
			'lab_test_template': 'test_template',
			'lab_test_description': 'test_description',
			'lab_test_rate': 'test_rate'
		}

		for new, old in rename_fields.items():
			if frappe.db.has_column('Lab Test Group Template', old):
				frappe.db.sql("""UPDATE `tabLab Test Group Template` SET {} = {}"""
					.format(new, old))

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
