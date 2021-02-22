import frappe
from frappe import _
from erpnext.stock.stock_ledger import update_entries_after
from erpnext.accounts.utils import update_gl_entries_after

def execute():
	data = frappe.db.sql(''' SELECT name, item_code, warehouse, voucher_type, voucher_no, posting_date, posting_time
		from `tabStock Ledger Entry` where creation > '2020-12-26 12:58:55.903836' and is_cancelled = 0
		order by timestamp(posting_date, posting_time) asc, creation asc''', as_dict=1)

	for index, d in enumerate(data):
		update_entries_after({
			"item_code": d.item_code,
			"warehouse": d.warehouse,
			"posting_date": d.posting_date,
			"posting_time": d.posting_time,
			"voucher_type": d.voucher_type,
			"voucher_no": d.voucher_no,
			"sle_id": d.name
		}, allow_negative_stock=True)

	frappe.db.auto_commit_on_many_writes = 1

	for row in frappe.get_all('Company', filters= {'enable_perpetual_inventory': 1}):
		update_gl_entries_after('2020-12-25', '01:58:55', company=row.name)

	frappe.db.auto_commit_on_many_writes = 0