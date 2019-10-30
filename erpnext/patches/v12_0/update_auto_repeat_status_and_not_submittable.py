from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def execute():
	#auto repeat is not submittable in v12
	frappe.reload_doctype("Auto Repeat")
	frappe.db.sql("update `tabDocPerm` set submit=0, cancel=0, amend=0 where parent='Auto Repeat'")
	frappe.db.sql("update `tabAuto Repeat` set docstatus=0 where docstatus=1 or docstatus=2")

	for entry in frappe.get_all('Auto Repeat'):
		doc = frappe.get_doc('Auto Repeat', entry.name)

		#create custom field for allow auto repeat 
		df = dict(fieldname='auto_repeat', label='Auto Repeat', fieldtype='Link', insert_after='sender',
			options='Auto Repeat', hidden=1, print_hide=1, read_only=1)
		create_custom_field(doc.reference_doctype, df)

		if doc.status in ['Draft', 'Stopped', 'Cancelled']:
			doc.disabled = 1

		#updates current status as Active, Disabled or Completed on validate
		doc.save()