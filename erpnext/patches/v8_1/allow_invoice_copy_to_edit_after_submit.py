import frappe

def execute():
	inv_copy_options = "ORIGINAL FOR RECIPIENT\nDUPLICATE FOR TRANSPORTER\nDUPLICATE FOR SUPPLIER\nTRIPLICATE FOR SUPPLIER"
	
	frappe.db.sql("""update `tabCustom Field` set allow_on_submit=1, options=%s
		where fieldname='invoice_copy' and dt = 'Sales Invoice'
	""", inv_copy_options)
	
	frappe.db.sql("""update `tabCustom Field` set read_only=1
		where fieldname='gst_state_number' and dt = 'Address'
	""")
