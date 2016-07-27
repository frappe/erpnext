# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Account")

	warehouses = frappe.db.sql_list("""select name from tabAccount
		where ifnull(account_type, '') = 'Stock' and ifnull(is_group, 0) = 0
		and warehouse is null""")
	if warehouses:
		warehouses = set_warehouse_for_stock_account(warehouses)

		stock_vouchers = frappe.db.sql("""select distinct sle.voucher_type, sle.voucher_no
			from `tabStock Ledger Entry` sle
			where sle.warehouse in (%s)
			order by sle.posting_date""" %
			', '.join(['%s']*len(warehouses)), tuple(warehouses))

		rejected = []
		for voucher_type, voucher_no in stock_vouchers:
			try:
				frappe.db.sql("""delete from `tabGL Entry`
					where voucher_type=%s and voucher_no=%s""", (voucher_type, voucher_no))

				voucher = frappe.get_doc(voucher_type, voucher_no)
				voucher.make_gl_entries()
				frappe.db.commit()
			except Exception, e:
				print frappe.get_traceback()
				rejected.append([voucher_type, voucher_no])
				frappe.db.rollback()

		print rejected

def set_warehouse_for_stock_account(warehouse_account):
	for account in warehouse_account:
		if frappe.db.exists('Warehouse', account):
			frappe.db.set_value("Account", account, "warehouse", account)
		else:
			warehouse_account.remove(account)

	return warehouse_account