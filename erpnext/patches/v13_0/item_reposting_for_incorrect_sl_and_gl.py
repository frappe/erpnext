import frappe
from frappe import _
from frappe.utils import getdate, get_time, today
from erpnext.stock.stock_ledger import update_entries_after
from erpnext.accounts.utils import update_gl_entries_after

def execute():
	for doctype in ('repost_item_valuation', 'stock_entry_detail', 'purchase_receipt_item',
			'purchase_invoice_item', 'delivery_note_item', 'sales_invoice_item', 'packed_item'):
		frappe.reload_doc('stock', 'doctype', doctype)
	frappe.reload_doc('buying', 'doctype', 'purchase_receipt_item_supplied')

	reposting_project_deployed_on = get_creation_time()
	posting_date = getdate(reposting_project_deployed_on)
	posting_time = get_time(reposting_project_deployed_on)

	if posting_date == today():
		return

	frappe.clear_cache()
	frappe.flags.warehouse_account_map = {}

	company_list = []

	data = frappe.db.sql('''
		SELECT
			name, item_code, warehouse, voucher_type, voucher_no, posting_date, posting_time, company
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
		if d.company not in company_list:
			company_list.append(d.company)

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

	if data:
		for row in frappe.get_all('Company', filters= {'enable_perpetual_inventory': 1}):
			if row.name in company_list:
				update_gl_entries_after(posting_date, posting_time, company=row.name)

	frappe.db.auto_commit_on_many_writes = 0

def get_creation_time():
	return frappe.db.sql(''' SELECT create_time FROM
		INFORMATION_SCHEMA.TABLES where TABLE_NAME = "tabRepost Item Valuation" ''', as_list=1)[0][0]