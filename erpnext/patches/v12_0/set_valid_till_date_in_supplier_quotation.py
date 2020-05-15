from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("buying", "doctype", "supplier_quotation")
	frappe.db.sql("""UPDATE `tabSupplier Quotation`
		SET valid_till = DATE_ADD(transaction_date , INTERVAL 1 MONTH)
		WHERE docstatus < 2""")
