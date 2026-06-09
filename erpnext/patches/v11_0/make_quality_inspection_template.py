# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "quality_inspection_template")
	frappe.reload_doc("stock", "doctype", "item")

	# Item.quality_inspection_template was removed in the Quality module refactor
	# (replaced by the Item Quality Trigger child table). This legacy patch only
	# populated that field, so it is now a no-op when the field is absent.
	if not frappe.get_meta("Item").has_field("quality_inspection_template"):
		return

	for data in frappe.get_all(
		"Item Quality Inspection Parameter", fields=["parent"], filters={"parenttype": "Item"}, distinct=True
	):
		qc_doc = frappe.new_doc("Quality Inspection Template")
		qc_doc.quality_inspection_template_name = "QIT/%s" % data.parent
		qc_doc.flags.ignore_mandatory = True
		qc_doc.save(ignore_permissions=True)

		frappe.db.set_value(
			"Item", data.parent, "quality_inspection_template", qc_doc.name, update_modified=False
		)
		frappe.db.sql(
			""" update `tabItem Quality Inspection Parameter`
			set parentfield = 'item_quality_inspection_parameter', parenttype = 'Quality Inspection Template',
			parent = %s where parenttype = 'Item' and parent = %s""",
			(qc_doc.name, data.parent),
		)

	# update field in item variant settings
	frappe.db.sql(
		""" update `tabVariant Field` set field_name = 'quality_inspection_template'
		where field_name = 'quality_parameters'"""
	)
