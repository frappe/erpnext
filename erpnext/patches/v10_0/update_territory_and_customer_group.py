import frappe
from frappe.model.rename_doc import update_linked_doctypes, get_fetch_fields

def execute():
	customers = frappe.get_all('Customer', fields=["name", "territory", "customer_group"])
	territory_fetch = get_fetch_fields('Customer', 'Territory')
	customer_group_fetch = get_fetch_fields('Customer', 'Customer Group')

	for customer in customers:
		# Update Territory across all transaction
		update_linked_doctypes(territory_fetch, customer.name, customer.territory_value)
		# Update Territory across all transaction
		update_linked_doctypes(customer_group_fetch, customer.name, customer.customer_group_value)
