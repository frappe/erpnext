import frappe
from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import on_doctype_update

def execute():
	frappe.db.sql("drop index posting_sort_index on `tabStock Ledger Entry`")
	on_doctype_update()
