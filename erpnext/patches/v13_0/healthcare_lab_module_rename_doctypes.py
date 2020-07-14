from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	lab_test_groups = []
	if frappe.db.exists('DocType', 'Lab Test Groups'):
		for d in frappe.db.sql("""
			SELECT
				name, template_or_new_line, lab_test_template, lab_test_rate, lab_test_description,
				group_event, group_test_uom, group_test_normal_range,
				parent, creation, owner
			FROM
				`tabLab Test Groups`
		""", as_dict=1):
			lab_test_groups.append((d.name, d.template_or_new_line, d.lab_test_template, d.lab_test_rate,
				d.lab_test_description, d.group_event, d.group_test_uom, d.group_test_normal_range,
				d.creation, d.owner, d.parent, 'Lab Test Template', 'lab_test_groups'))

	normal_tests = []
	if frappe.db.exists('DocType', 'Normal Test Items'):
		for d in frappe.db.sql("""
			SELECT
				name, lab_test_name, lab_test_event, result_value, lab_test_uom,
				normal_range, lab_test_comment, require_result_value, template,
				parent, creation, owner
			FROM
				`tabNormal Test Items`
		""", as_dict=1):
			normal_tests.append((d.name, d.lab_test_name, d.lab_test_event, d.result_value,
				d.lab_test_uom, d.normal_range, d.lab_test_comment, d.require_result_value, d.template,
				d.creation, d.owner, d.parent, 'Lab Test', 'normal_test_items'))

	sensitivity_tests = []
	if frappe.db.exists('DocType', 'Sensitivity Test Items'):
		for d in frappe.db.sql("""
			SELECT
				name, antibiotic, antibiotic_sensitivity,
				parent, creation, owner
			FROM
				`tabSensitivity Test Items`
		""", as_dict=1):
			sensitivity_tests.append((d.name, d.antibiotic, d.antibiotic_sensitivity,
				d.creation, d.owner, d.parent, 'Lab Test', 'sensitivity_test_items'))

	special_test_templates = []
	if frappe.db.exists('DocType', 'Special Test Template'):
		for d in frappe.db.sql("""
			SELECT
				name, particulars, parent, creation, owner
			FROM
				`tabSpecial Test Template`
		""", as_dict=1):
			special_test_templates.append((d.name, d.particulars, d.creation, d.owner, d.parent,
				'Lab Test Template', 'descriptive_test_templates'))

	special_tests = []
	if frappe.db.exists('DocType', 'Special Test Items'):
		for d in frappe.db.sql("""
			SELECT
				name, lab_test_particulars, result_value, require_result_value, template,
				parent, creation, owner
			FROM
				`tabSpecial Test Items`
		""", as_dict=1):
			special_tests.append((d.name, d.lab_test_particulars, d.result_value, d.require_result_value,
				d.template, d.creation, d.owner, d.parent, 'Lab Test', 'descriptive_test_items'))

	# Rename doctypes
	doctypes = {
		'Lab Test Groups': 'Lab Test Group Template',
		'Normal Test Items': 'Normal Test Result',
		'Sensitivity Test Items': 'Sensitivity Test Result',
		'Special Test Items': 'Descriptive Test Result',
		'Special Test Template': 'Descriptive Test Template'
	}

	for old_dt, new_dt in doctypes.items():
		if not frappe.db.table_exists(new_dt) and frappe.db.table_exists(old_dt):
			frappe.rename_doc('DocType', old_dt, new_dt, force=True)
			frappe.reload_doc('healthcare', 'doctype', frappe.scrub(new_dt))
			frappe.delete_doc('DocType', old_dt)

	if frappe.db.exists('DocType', 'Lab Test Template'):
		frappe.reload_doc('healthcare', 'doctype', 'lab_test_template')
		if lab_test_groups:
			frappe.db.sql("""
				INSERT INTO `tabLab Test Group Template`
					(name, template_or_new_line, lab_test_template, lab_test_rate, lab_test_description,
					group_event, group_test_uom, group_test_normal_range,
					creation, owner, parent, parenttype, parentfield)
				VALUES {}""".format(', '.join(['%s'] * len(lab_test_groups))), tuple(lab_test_groups)
			)

		if special_test_templates:
			frappe.db.sql("""
				INSERT INTO `tabDescriptive Test Template`
					(name, particulars, creation, owner, parent, parenttype, parentfield)
				VALUES {}""".format(', '.join(['%s'] * len(special_test_templates))), tuple(special_test_templates)
			)

	if frappe.db.exists('DocType', 'Lab Test'):
		frappe.reload_doc('healthcare', 'doctype', 'lab_test')
		if normal_tests:
			frappe.db.sql("""
				INSERT INTO `tabNormal Test Result`
					(name, lab_test_name, lab_test_event, result_value, lab_test_uom,
					normal_range, lab_test_comment, require_result_value, template,
					creation, owner, parent, parenttype, parentfield)
				VALUES {}""".format(', '.join(['%s'] * len(normal_tests))), tuple(normal_tests)
			)

		if sensitivity_tests:
			frappe.db.sql("""
				INSERT INTO `tabSensitivity Test Result`
					(name, antibiotic, antibiotic_sensitivity,
					creation, owner, parent, parenttype, parentfield)
				VALUES {}""".format(', '.join(['%s'] * len(sensitivity_tests))), tuple(sensitivity_tests)
			)

		if special_tests:
			frappe.db.sql("""
				INSERT INTO `tabDescriptive Test Result`
					(name, lab_test_particulars, result_value, require_result_value, template,
					creation, owner, parent, parenttype, parentfield)
				VALUES {}""".format(', '.join(['%s'] * len(special_tests))), tuple(special_tests)
			)

		if frappe.db.has_column('Lab Test', 'special_toggle'):
			rename_field('Lab Test', 'special_toggle', 'descriptive_toggle')

	# Fix Options
	if frappe.db.exists('DocType', 'Lab Test Group Template'):
		frappe.reload_doc('healthcare', 'doctype', 'lab_test_group_template')
		frappe.db.sql("""update `tabLab Test Group Template` set template_or_new_line = 'Add New Line'
				where template_or_new_line = 'Add new line'""")