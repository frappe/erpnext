import frappe
from erpnext.regional.india.setup  import make_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	make_custom_fields()

	frappe.db.sql("""
		update `tabCustom Field`
		set reqd = 0, `default` = ''
		where fieldname = 'reason_for_issuing_document'
	""")

	frappe.db.sql("""delete from `tabCustom Field` where dt = 'Purchase Invoice'
		and fieldname in ('port_code', 'shipping_bill_number', 'shipping_bill_date')""")