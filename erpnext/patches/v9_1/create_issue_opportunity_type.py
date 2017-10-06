# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Issue Type")
	frappe.reload_doctype("Opportunity Type")

	for doctype in ["Issue", "Opportunity"]:
		meta = frappe.get_meta(doctype)
		issue_opportunity_type_doctype = "{0} Type".format(doctype)
		fieldnames = [frappe.scrub(issue_opportunity_type_doctype)]

		frappe.reload_doctype(issue_opportunity_type_doctype)
		if doctype == "Opportunity":
			# to create the Opportunity Type (enquiry_type)
			fieldnames.append("enquiry_type")

		for fieldname in fieldnames:
			field  = meta.get("fields", {"fieldname": fieldname})
			if field and field[0]:
				create_type_documents(doctype, issue_opportunity_type_doctype, field[0])
				convert_custom_field(doctype, issue_opportunity_type_doctype, fieldname)

def create_type_documents(doctype, issue_opportunity_type_doctype, field):
	""" create `{doctype} Type` documents from field options """
	def create_new_doc(doctype, issue_opportunity_type=None):
		if not issue_opportunity_type:
			return

		if frappe.db.exists(doctype, issue_opportunity_type):
			return

		try:
			fieldname = frappe.scrub(doctype)
			frappe.get_doc({
				"doctype": doctype,
				fieldname: issue_opportunity_type
			}).insert(ignore_permissions=True)
		except Exception as e:
			pass

	issue_opportunity_types = []
	if field.fieldtype == "Select":
		issue_opportunity_types = field.options.split("\n") if field.options else []
	elif field.fieldtype == "Data":
		results = frappe.get_all(doctype, fields=[field.fieldname], distinct=True) or []
		issue_opportunity_types = [row.get(field.fieldname) for row in results \
			if row.get(field.fieldname, None)]

	for issue_opportunity_type in issue_opportunity_types:
		create_new_doc(issue_opportunity_type_doctype,
			issue_opportunity_type=issue_opportunity_type)

def convert_custom_field(doctype, issue_opportunity_type_doctype, fieldname):
	""" delete the property setter's if available, convert the `{doctype}_type` field options """
	property_setter = frappe.db.get_value("Property Setter", {
		"doc_type": doctype,
		"field_name": fieldname,
		"property": "options"
	})
	if property_setter:
		frappe.delete_doc("Property Setter", property_setter, ignore_permissions=True)

	custom_field = frappe.db.get_value("Custom Field", {"fieldname": fieldname})
	if custom_field:
		frappe.delete_doc("Custom Field", custom_field, ignore_permissions=True)