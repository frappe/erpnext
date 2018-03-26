# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.stock.utils import get_bin

def execute():
	item_warehouse_list = frappe.db.sql("""
		select distinct rm_item_code, reserve_warehouse
		from `tabPurchase Order Item Supplied`
		where docstatus=1 and reserve_warehouse is not null and reserve_warehouse != ''
	""", as_list=1)

	for d in frappe.db.sql("""select distinct item_code, source_warehouse
		from `tabProduction Order Item`
		where docstatus=1 and source_warehouse is not null and source_warehouse != ''""", as_list=1):
		if [d[0], d[1]] not in item_warehouse_list:
			item_warehouse_list.append([d[0], d[1]])

	for b in item_warehouse_list:
		try:
			bin_doc = get_bin(b[0], b[1])
			bin_doc.update_reserved_qty_for_production()
			bin_doc.update_reserved_qty_for_sub_contracting()
		except:
			pass