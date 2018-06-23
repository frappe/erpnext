# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	# rename the School module as Education

	# rename the school module
	if frappe.db.exists('Module Def', 'Schools') and not frappe.db.exists('Module Def', 'Education'):
		frappe.rename_doc("Module Def", "Schools", "Education")

	# delete the school module
	if frappe.db.exists('Module Def', 'Schools') and frappe.db.exists('Module Def', 'Education'):
		frappe.db.sql("""delete from `tabModule Def` where module_name = 'Schools'""")


	# rename "School Settings" to the "Education Settings
	if frappe.db.exists('DocType', 'School Settings'):
		frappe.rename_doc("DocType", "School Settings", "Education Settings", force=True)
		frappe.reload_doc("education", "doctype", "education_settings")

	# delete the discussion web form if exists
	if frappe.db.exists('Web Form', 'Discussion'):
		frappe.db.sql("""delete from `tabWeb Form` where name = 'discussion'""")

	# rename the select option field from "School Bus" to "Institute's Bus"
	frappe.reload_doc("education", "doctype", "Program Enrollment")
	if "mode_of_transportation" in frappe.db.get_table_columns("Program Enrollment"):
		frappe.db.sql("""update `tabProgram Enrollment` set mode_of_transportation = "Institute's Bus"
			where mode_of_transportation = "School Bus" """)
