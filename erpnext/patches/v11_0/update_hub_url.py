import frappe

def execute():
	frappe.reload_doc('hub_node', 'doctype', 'Marketplace Settings')
	frappe.db.set_value('Marketplace Settings', 'Marketplace Settings', 'hub_url', 'https://hubmarket.org')
