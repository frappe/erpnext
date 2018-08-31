import frappe

def execute():
	frappe.reload_doc('hub_node', 'doctype', 'Hub Settings')
	frappe.db.set_value('Hub Settings', 'Hub Settings', 'hub_url', 'https://hubmarket.org')
