from __future__ import unicode_literals
import frappe

def execute():
	if "purchase_receipt" not in frappe.db.get_table_columns("Landed Cost Purchase Receipt"):
		return
		
	frappe.reload_doctype("Landed Cost Purchase Receipt")
	
	frappe.db.sql("""
		update `tabLanded Cost Purchase Receipt`
		set receipt_document_type = 'Purchase Receipt', receipt_document = purchase_receipt
		where (receipt_document is null or receipt_document = '')
			and (purchase_receipt is not null and purchase_receipt != '')
	""")