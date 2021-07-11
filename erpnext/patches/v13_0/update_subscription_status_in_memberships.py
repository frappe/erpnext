import frappe

def execute():
	if 'Non Profit' in frappe.get_active_domains() and frappe.db.exists('DocType', 'Member'):
		frappe.reload_doc('Non Profit', 'doctype', 'Member')
		frappe.db.sql('UPDATE `tabMember` SET subscription_status = "Active" WHERE subscription_activated = 1')