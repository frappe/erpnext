import frappe


def execute():
	frappe.db.sql("update `tabSales Team` set commission_rate = 0 where commission_rate is null")
	frappe.db.sql("update `tabSales Person` set commission_rate = 0 where commission_rate is null")
	frappe.reload_doc("selling", "doctype", "sales_team")
	frappe.reload_doc("setup", "doctype", "sales_person")
