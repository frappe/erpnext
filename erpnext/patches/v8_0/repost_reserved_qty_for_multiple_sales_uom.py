# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.stock.stock_balance import update_bin_qty, get_reserved_qty

def execute():
	for doctype in ("Sales Order Item", "Bin"):
		frappe.reload_doctype(doctype)

	repost_for = frappe.db.sql("""select distinct item_code, warehouse
		from `tabSales Order Item` where docstatus=1 and uom != stock_uom and
		exists(select name from tabItem where name=`tabSales Order Item`.item_code and ifnull(is_stock_item, 0)=1)""")

	for item_code, warehouse in repost_for:
		update_bin_qty(item_code, warehouse, {
			"reserved_qty": get_reserved_qty(item_code, warehouse)
		})