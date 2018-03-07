import frappe
from erpnext.regional.india.setup  import make_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	for doctype in ["Sales Invoice", "Delivery Note", "Purchase Invoice"]:
		frappe.db.sql("""delete from `tabCustom Field` where dt = %s
			and fieldname in ('port_code', 'shipping_bill_number', 'shipping_bill_date')""", doctype)

	make_custom_fields()

	frappe.db.sql("""
		update `tabCustom Field`
		set reqd = 0, `default` = ''
		where fieldname = 'reason_for_issuing_document'
	""")
	
	
