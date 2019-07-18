from __future__ import unicode_literals
import frappe
from erpnext.regional.india.setup import make_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})

	if not company:
		return

	field = frappe.db.get_value("Custom Field", {"dt": "Sales Invoice", "fieldname": "ewaybill"})

	if field:
		ewaybill_field = frappe.get_doc("Custom Field", field)

		ewaybill_field.flags.ignore_validate = True

		ewaybill_field.update({
			'fieldname': 'ewaybill',
			'label': 'e-Way Bill No.',
			'fieldtype': 'Data',
			'depends_on': 'eval:(doc.docstatus === 1)',
			'allow_on_submit': 1,
			'insert_after': 'tax_id',
			'translatable': 0
		})

		ewaybill_field.save()