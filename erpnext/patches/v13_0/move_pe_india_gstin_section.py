import frappe


def execute():
	frappe.db.sql("UPDATE `tabCustom Field` SET `insert_after` = 'losses' WHERE `name` = 'Payment Entry-gst_section'")
