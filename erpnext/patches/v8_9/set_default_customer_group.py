import frappe

def execute():
	selling_settings = frappe.get_single('Selling Settings')
	selling_settings.set_default_customer_group_and_territory()
	selling_settings.save()
