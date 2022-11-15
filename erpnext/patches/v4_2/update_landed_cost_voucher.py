# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doc("stock", "doctype", "landed_cost_voucher")
	frappe.db.sql("""update `tabLanded Cost Voucher` set distribute_charges_based_on = 'Amount'
		where docstatus=1""")
