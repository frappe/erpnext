import frappe
from erpnext.regional.india.setup import setup
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	hsn_sac_field = dict(fieldname='gst_hsn_code', label='HSN/SAC',
		fieldtype='Data', options='item_code.gst_hsn_code', insert_after='description',
		allow_on_submit=1, print_hide=1)

	custom_fields = {
		'Material Request Item': [hsn_sac_field]
	}

	create_custom_fields(custom_fields)
