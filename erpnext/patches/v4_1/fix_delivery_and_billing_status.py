# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql("""update `tabSales Order` set delivery_status = 'Not Delivered'
		where delivery_status = 'Delivered' and ifnull(per_delivered, 0) = 0 and ifnull(docstatus, 0) in (0, 1)""")

	frappe.db.sql("""update `tabSales Order` set billing_status = 'Not Billed'
		where billing_status = 'Billed' and ifnull(per_billed, 0) = 0 and ifnull(docstatus, 0) in (0, 1)""")
