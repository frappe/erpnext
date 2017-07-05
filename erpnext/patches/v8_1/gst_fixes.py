import frappe

def execute():
	frappe.db.sql("""update `tabCustom Field` set label = 'HSN/SAC Code'
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
	
	# reload gst print format for Indian users
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if company:
		frappe.reload_doc("regional", "print_format", "gst_tax_invoice")