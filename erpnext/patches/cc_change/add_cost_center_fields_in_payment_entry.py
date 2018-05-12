# V 1.0.1

from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	make_custom_fields()

def make_custom_fields():
	cost_center_fields = [
		dict(	fieldname='cost_center_from', label='Cost Center From', fieldtype='Link',
			insert_after='paid_from', options='Cost Center', hidden=1
		),
		dict(	fieldname='cost_center_to', label='Cost Center To', fieldtype='Link',
			insert_after='paid_to', options='Cost Center', hidden=1
		),

	]	

	custom_fields = {
		"Payment Entry": cost_center_fields,
	}	

	create_custom_fields(custom_fields)

	frappe.get_doc("DocType", "Payment Entry").run_module_method("on_doctype_update")
