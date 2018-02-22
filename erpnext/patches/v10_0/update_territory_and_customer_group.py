import frappe
from frappe.model.rename_doc import update_linked_doctypes

def execute():
	customers = frappe.get_all('Customer')
	for customer in customers:
		# Update Territory across all transaction
		terr = frappe.get_value('Customer', customer, 'territory')
		update_linked_doctypes("Customer", "Territory", customer.name, terr)

		# Update Territory across all transaction
		cust_group = frappe.get_value('Customer', customer, 'customer_group')
		update_linked_doctypes("Customer", "Customer Group", customer.name, cust_group)
