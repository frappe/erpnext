from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter, delete_property_setter

def execute():
	frappe.reload_doc("projects", "doctype", "project")

	frappe.db.sql("""UPDATE `tabProject`
		SET
			naming_series = 'PROJ-.####'
		WHERE
			naming_series is NULL""")

