# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("accounting", "doctype", "pricing_rule")
	frappe.db.sql("""update `tabPricing Rule` set selling=1 where ifnull(applicable_for, '') in
		('', 'Customer', 'Customer Group', 'Territory', 'Sales Partner', 'Campaign')""")

	frappe.db.sql("""update `tabPricing Rule` set buying=1 where ifnull(applicable_for, '') in
		('', 'Supplier', 'Supplier Type')""")
