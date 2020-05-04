from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from erpnext.regional.address_template.setup import set_up_address_templates


def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	update_existing_custom_fields()
	add_custom_fields()
	set_up_address_templates(default_country='India')
	frappe.reload_doc("regional", "print_format", "gst_tax_invoice")


def update_existing_custom_fields():
	frappe.db.sql("""update `tabCustom Field` set label = 'HSN/SAC'
		where fieldname='gst_hsn_code' and label='GST HSN Code'
	""")

	frappe.db.sql("""update `tabCustom Field` set print_hide = 1
		where fieldname in ('customer_gstin', 'supplier_gstin', 'company_gstin')
	""")

	frappe.db.sql("""update `tabCustom Field` set insert_after = 'address_display'
		where fieldname in ('customer_gstin', 'supplier_gstin')
	""")

	frappe.db.sql("""update `tabCustom Field` set insert_after = 'company_address_display'
		where fieldname = 'company_gstin'
	""")

	frappe.db.sql("""update `tabCustom Field` set insert_after = 'description'
		where fieldname='gst_hsn_code' and dt in ('Sales Invoice Item', 'Purchase Invoice Item')
	""")


def add_custom_fields():
	hsn_sac_field = dict(fieldname='gst_hsn_code', label='HSN/SAC',
		fieldtype='Data', options='item_code.gst_hsn_code', insert_after='description')

	custom_fields = {
		'Address': [
			dict(fieldname='gst_state_number', label='GST State Number',
				fieldtype='Int', insert_after='gst_state'),
		],
		'Sales Invoice': [
			dict(fieldname='invoice_copy', label='Invoice Copy',
				fieldtype='Select', insert_after='project', print_hide=1, allow_on_submit=1,
				options='ORIGINAL FOR RECIPIENT\nDUPLICATE FOR TRANSPORTER\nTRIPLICATE FOR SUPPLIER'),
		],
		'Sales Order Item': [hsn_sac_field],
		'Delivery Note Item': [hsn_sac_field],
		'Purchase Order Item': [hsn_sac_field],
		'Purchase Receipt Item': [hsn_sac_field]
	}

	for doctype, fields in custom_fields.items():
		for df in fields:
			create_custom_field(doctype, df)
