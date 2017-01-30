import frappe

def execute():
	# removing Open status for Customer / Supplier as it is duplicate
	options = frappe.get_meta('Customer').get_field('status').options.split('\n')
	default_option = 'Active'
	if not default_option in options:
		default_option = option[0]

	frappe.db.sql('update tabCustomer set status=%s where status="Open"', default_option)