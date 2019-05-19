from __future__ import unicode_literals
import frappe, os
from frappe import _

def execute():
	frappe.reload_doc("stock", "doctype", "stock_ledger_entry")

	frappe.db.sql("""
		update `tabStock Ledger Entry` sle
		inner join `tabDelivery Note` t on sle.voucher_type='Delivery Note' and sle.voucher_no=t.name
		set sle.party_type = 'Customer', sle.party = t.customer
	""")

	frappe.db.sql("""
		update `tabStock Ledger Entry` sle
		inner join `tabSales Invoice` t on sle.voucher_type='Sales Invoice' and sle.voucher_no=t.name
		set sle.party_type = 'Customer', sle.party = t.customer
	""")

	frappe.db.sql("""
		update `tabStock Ledger Entry` sle
		inner join `tabPurchase Receipt` t on sle.voucher_type='Purchase Receipt' and sle.voucher_no=t.name
		set sle.party_type = 'Supplier', sle.party = t.supplier
	""")

	frappe.db.sql("""
		update `tabStock Ledger Entry` sle
		inner join `tabPurchase Invoice` t on sle.voucher_type='Purchase Invoice' and sle.voucher_no=t.name
		set sle.party_type = 'Supplier', sle.party = t.supplier
	""")
