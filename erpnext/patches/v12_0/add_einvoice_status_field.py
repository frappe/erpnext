from __future__ import unicode_literals
import json
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	# move hidden einvoice fields to a different section
	custom_fields = {
		'Sales Invoice': [
			dict(fieldname='einvoice_section', label='E-Invoice Fields', fieldtype='Section Break', insert_after='gst_vehicle_type',
			print_hide=1, hidden=1),
		
			dict(fieldname='ack_no', label='Ack. No.', fieldtype='Data', read_only=1, hidden=1, insert_after='einvoice_section',
				no_copy=1, print_hide=1),
			
			dict(fieldname='ack_date', label='Ack. Date', fieldtype='Data', read_only=1, hidden=1, insert_after='ack_no', no_copy=1, print_hide=1),

			dict(fieldname='irn_cancel_date', label='Cancel Date', fieldtype='Data', read_only=1, hidden=1, insert_after='ack_date', 
				no_copy=1, print_hide=1),

			dict(fieldname='signed_einvoice', label='Signed E-Invoice', fieldtype='Code', options='JSON', hidden=1, insert_after='irn_cancel_date',
				no_copy=1, print_hide=1, read_only=1),

			dict(fieldname='signed_qr_code', label='Signed QRCode', fieldtype='Code', options='JSON', hidden=1, insert_after='signed_einvoice',
				no_copy=1, print_hide=1, read_only=1),

			dict(fieldname='qrcode_image', label='QRCode', fieldtype='Attach Image', hidden=1, insert_after='signed_qr_code',
				no_copy=1, print_hide=1, read_only=1),

			dict(fieldname='einvoice_status', label='E-Invoice Status', fieldtype='Select', insert_after='qrcode_image',
				options='\nPending\nGenerated\nCancelled\nFailed', default=None, hidden=1, no_copy=1, print_hide=1, read_only=1),

			dict(fieldname='failure_description', label='E-Invoice Failure Description', fieldtype='Code', options='JSON',
				hidden=1, insert_after='einvoice_status', no_copy=1, print_hide=1, read_only=1)
		]
	}
	create_custom_fields(custom_fields, update=True)

	if frappe.db.exists('E Invoice Settings') and frappe.db.get_single_value('E Invoice Settings', 'enable'):
		frappe.db.sql('''
			UPDATE `tabSales Invoice` SET einvoice_status = 'Pending'
			WHERE
				posting_date >= '2021-04-01'
				AND ifnull(irn, '') = ''
				AND ifnull(`billing_address_gstin`, '') != ifnull(`company_gstin`, '')
				AND ifnull(gst_category, '') in ('Registered Regular', 'SEZ', 'Overseas', 'Deemed Export')
		''')

		# set appropriate statuses
		frappe.db.sql('''UPDATE `tabSales Invoice` SET einvoice_status = 'Generated'
			WHERE ifnull(irn, '') != '' AND ifnull(irn_cancelled, 0) = 0''')

		frappe.db.sql('''UPDATE `tabSales Invoice` SET einvoice_status = 'Cancelled'
			WHERE ifnull(irn_cancelled, 0) = 1''')

	# set correct acknowledgement in e-invoices
	einvoices = frappe.get_all('Sales Invoice', {'irn': ['is', 'set']}, ['name', 'signed_einvoice'])

	if einvoices:
		for inv in einvoices:
			signed_einvoice = inv.get('signed_einvoice')
			if signed_einvoice:
				signed_einvoice = json.loads(signed_einvoice)
				frappe.db.set_value('Sales Invoice', inv.get('name'), 'ack_no', signed_einvoice.get('AckNo'), update_modified=False)
				frappe.db.set_value('Sales Invoice', inv.get('name'), 'ack_date', signed_einvoice.get('AckDt'), update_modified=False)