# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.stock.utils import get_bin

def execute():
	frappe.reload_doc("stock", "doctype", "bin")
	frappe.reload_doc("buying", "doctype", "purchase_order_item_supplied")
	for d in frappe.db.sql("""
		select distinct rm_item_code, reserve_warehouse
		from `tabPurchase Order Item Supplied`
		where docstatus=1 and reserve_warehouse is not null and reserve_warehouse != ''"""):

		try:
			bin_doc = get_bin(d[0], d[1])
			bin_doc.update_reserved_qty_for_sub_contracting()
		except:
			pass

	for d in frappe.db.sql("""select distinct item_code, source_warehouse
		from `tabWork Order Item`
		where docstatus=1 and transferred_qty > required_qty
			and source_warehouse is not null and source_warehouse != ''""", as_list=1):

		try:
			bin_doc = get_bin(d[0], d[1])
			bin_doc.update_reserved_qty_for_production()
		except:
			pass
