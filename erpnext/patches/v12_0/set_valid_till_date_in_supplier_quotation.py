from __future__ import unicode_literals
import frappe

def execute():
	reload_doc("buying", "doctype", "suppplier_quotation")
	frappe.db.sql("""UPDATE `tabSupplier Quotation`
		SET valid_till = DATE_ADD(transaction_date , INTERVAL 1 MONTH)
		WHERE docstatus < 2""")