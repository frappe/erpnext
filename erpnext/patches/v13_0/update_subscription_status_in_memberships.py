import frappe


def execute():
	if frappe.db.exists("DocType", "Member"):
		frappe.reload_doc("Non Profit", "doctype", "Member")

		if frappe.db.has_column("Member", "subscription_activated"):
			frappe.db.set_value(
				"Member",
				{"subscription_activated": 1},
				"subscription_status",
				"Active",
				update_modified=False,
			)
			frappe.db.sql_ddl("ALTER table `tabMember` DROP COLUMN subscription_activated")
