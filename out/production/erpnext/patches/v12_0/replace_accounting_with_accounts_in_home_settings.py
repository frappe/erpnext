import frappe


def execute():
	frappe.db.sql("""UPDATE `tabUser` SET `home_settings` = REPLACE(`home_settings`, 'Accounting', 'Accounts')""")
	frappe.cache().delete_key('home_settings')
