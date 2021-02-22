import frappe
from frappe import _
from erpnext.stock.stock_ledger import update_entries_after
from erpnext.accounts.utils import update_gl_entries_after

def execute():
	frappe.reload_doc('Stock', 'doctype', 'repost_item_valuation')

	reposting_project_deployed_on = frappe.db.get_value("DocType", "Repost Item Valuation", "creation")

	data = frappe.db.sql('''
		SELECT
			name, item_code, warehouse, voucher_type, voucher_no, posting_date, posting_time
		FROM
			`tabStock Ledger Entry`
		WHERE
			creation > %s
			and is_cancelled = 0
		ORDER BY timestamp(posting_date, posting_time) asc, creation asc
	''', reposting_project_deployed_on, as_dict=1)

	frappe.db.auto_commit_on_many_writes = 1
	print("Reposting Stock Ledger Entries...")
	total_sle = len(data)
	i = 0
	for d in data:
		update_entries_after({
			"item_code": d.item_code,
			"warehouse": d.warehouse,
			"posting_date": d.posting_date,
			"posting_time": d.posting_time,
			"voucher_type": d.voucher_type,
			"voucher_no": d.voucher_no,
			"sle_id": d.name
		}, allow_negative_stock=True)

		i += 1
		if i%100 == 0:
			print(i, "/", total_sle)


	print("Reposting General Ledger Entries...")
	for row in frappe.get_all('Company', filters= {'enable_perpetual_inventory': 1}):
		update_gl_entries_after('2020-12-25', '01:58:55', company=row.name)

	frappe.db.auto_commit_on_many_writes = 0