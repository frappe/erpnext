# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
	frappe.reload_doc('stock', 'doctype', 'quality_inspection_template')
	frappe.reload_doc('stock', 'doctype', 'item')

	for data in frappe.get_all('Item Quality Inspection Parameter',
		fields = ["distinct parent"], filters = {'parenttype': 'Item'}):
		qc_doc = frappe.new_doc("Quality Inspection Template")
		qc_doc.quality_inspection_template_name = 'QIT/%s' % data.parent
		qc_doc.flags.ignore_mandatory = True
		qc_doc.save(ignore_permissions=True)

		frappe.db.set_value('Item', data.parent, "quality_inspection_template", qc_doc.name, update_modified=False)
		frappe.db.sql(""" update `tabItem Quality Inspection Parameter`
			set parentfield = 'item_quality_inspection_parameter', parenttype = 'Quality Inspection Template',
			parent = %s where parenttype = 'Item' and parent = %s""", (qc_doc.name, data.parent))

	# update field in item variant settings
	frappe.db.sql(""" update `tabVariant Field` set field_name = 'quality_inspection_template'
		where field_name = 'quality_parameters'""")
