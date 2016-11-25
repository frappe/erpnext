# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from erpnext.controllers.stock_controller import get_warehouse_account, update_gl_entries_after

def execute():
	if not cint(frappe.defaults.get_global_default("auto_accounting_for_stock")):
		return

	frappe.reload_doc('accounts', 'doctype', 'sales_invoice')
	
	frappe.reload_doctype("Purchase Invoice")	
	wh_account = get_warehouse_account()
	
	for pi in frappe.get_all("Purchase Invoice", filters={"docstatus": 1, "update_stock": 1}):
		pi_doc = frappe.get_doc("Purchase Invoice", pi.name)
		items, warehouses = pi_doc.get_items_and_warehouses()
		update_gl_entries_after(pi_doc.posting_date, pi_doc.posting_time, warehouses, items, wh_account)
		
		frappe.db.commit()