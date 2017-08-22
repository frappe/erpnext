# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import print_function, unicode_literals
import frappe
from frappe.utils import flt

def execute():
	from erpnext.stock.stock_balance import repost
	repost(allow_zero_rate=True, only_actual=True)
	
	frappe.reload_doctype("Account")

	warehouse_account = frappe.db.sql("""select name, master_name from tabAccount
		where ifnull(account_type, '') = 'Warehouse'""")
	if warehouse_account:
		warehouses = [d[1] for d in warehouse_account]
		accounts = [d[0] for d in warehouse_account]

		stock_vouchers = frappe.db.sql("""select distinct sle.voucher_type, sle.voucher_no
			from `tabStock Ledger Entry` sle
			where sle.warehouse in (%s)
			order by sle.posting_date""" %
			', '.join(['%s']*len(warehouses)), tuple(warehouses))

		rejected = []
		for voucher_type, voucher_no in stock_vouchers:
			stock_bal = frappe.db.sql("""select sum(stock_value_difference) from `tabStock Ledger Entry`
				where voucher_type=%s and voucher_no =%s and warehouse in (%s)""" %
				('%s', '%s', ', '.join(['%s']*len(warehouses))), tuple([voucher_type, voucher_no] + warehouses))

			account_bal = frappe.db.sql("""select ifnull(sum(ifnull(debit, 0) - ifnull(credit, 0)), 0)
				from `tabGL Entry`
				where voucher_type=%s and voucher_no =%s and account in (%s)
				group by voucher_type, voucher_no""" %
				('%s', '%s', ', '.join(['%s']*len(accounts))), tuple([voucher_type, voucher_no] + accounts))

			if stock_bal and account_bal and abs(flt(stock_bal[0][0]) - flt(account_bal[0][0])) > 0.1:
				try:
					print(voucher_type, voucher_no, stock_bal[0][0], account_bal[0][0])

					frappe.db.sql("""delete from `tabGL Entry`
						where voucher_type=%s and voucher_no=%s""", (voucher_type, voucher_no))

					voucher = frappe.get_doc(voucher_type, voucher_no)
					voucher.make_gl_entries(repost_future_gle=False)
					frappe.db.commit()
				except Exception as e:
					print(frappe.get_traceback())
					rejected.append([voucher_type, voucher_no])
					frappe.db.rollback()

		print("Failed to repost: ")
		print(rejected)
