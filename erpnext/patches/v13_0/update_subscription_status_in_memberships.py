import frappe


def execute():
	if frappe.db.exists('DocType', 'Member'):
		frappe.reload_doc('Non Profit', 'doctype', 'Member')

		if frappe.db.has_column('Member', 'subscription_activated'):
			frappe.db.sql('UPDATE `tabMember` SET subscription_status = "Active" WHERE subscription_activated = 1')
			frappe.db.sql_ddl('ALTER table `tabMember` DROP COLUMN subscription_activated')
