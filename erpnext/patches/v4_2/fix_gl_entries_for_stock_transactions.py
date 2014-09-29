# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	warehouses_with_account = frappe.db.sql_list("""select master_name from tabAccount
		where ifnull(account_type, '') = 'Warehouse'""")

	stock_vouchers_without_gle = frappe.db.sql("""select distinct sle.voucher_type, sle.voucher_no
		from `tabStock Ledger Entry` sle
		where sle.warehouse in (%s)
		and not exists(select name from `tabGL Entry`
			where voucher_type=sle.voucher_type and voucher_no=sle.voucher_no)
		order by sle.posting_date""" %
		', '.join(['%s']*len(warehouses_with_account)), tuple(warehouses_with_account))

	for voucher_type, voucher_no in stock_vouchers_without_gle:
		print voucher_type, voucher_no
		frappe.db.sql("""delete from `tabGL Entry`
			where voucher_type=%s and voucher_no=%s""", (voucher_type, voucher_no))

		voucher = frappe.get_doc(voucher_type, voucher_no)
		voucher.make_gl_entries()
		frappe.db.commit()
