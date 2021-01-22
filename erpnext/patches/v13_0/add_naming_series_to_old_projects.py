from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter, delete_property_setter

def execute():
	frappe.reload_doc("projects", "doctype", "project")
	projects = frappe.db.get_all("Project",
		fields=["name", "naming_series", "modified"],
		filters={
			"naming_series": ["is", "not set"]
		},
		order_by="timestamp(modified) asc")

	# disable set only once as the old docs must be saved
	# (to bypass 'Cant change naming series' validation on save)
	make_property_setter("Project", "naming_series", "set_only_once", 0, "Check")

	for entry in projects:
		# need to save the doc so that users can edit old projects
		doc = frappe.get_doc("Project", entry.name)
		if not doc.naming_series:
			doc.naming_series = "PROJ-.####"
			doc.save()

	delete_property_setter("Project", "set_only_once", "naming_series")
	frappe.db.commit()
