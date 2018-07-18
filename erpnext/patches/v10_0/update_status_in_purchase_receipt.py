import frappe

def execute():
	frappe.reload_doc("stock", "doctype", "purchase_receipt")
	frappe.db.sql('''
		UPDATE `tabPurchase Receipt` SET status = "Completed" WHERE per_billed = 100 AND docstatus = 1
	''')