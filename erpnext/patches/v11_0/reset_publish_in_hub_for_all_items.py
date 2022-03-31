import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "item")
	frappe.db.sql("""update `tabItem` set publish_in_hub = 0""")
