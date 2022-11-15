# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.db.sql("""update `tabStock Ledger Entry` sle, tabItem item
		set sle.stock_uom = item.stock_uom
		where sle.voucher_type="Delivery Note" and item.name = sle.item_code
		and sle.stock_uom != item.stock_uom""")
