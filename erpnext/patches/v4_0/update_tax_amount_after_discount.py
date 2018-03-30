# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "sales_taxes_and_charges")
	docs_with_discount_amount = frappe._dict()
	for dt in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
		records = frappe.db.sql_list("""select name from `tab%s`
			where ifnull(discount_amount, 0) > 0 and docstatus=1""" % dt)
		docs_with_discount_amount[dt] = records

	for dt, discounted_records in docs_with_discount_amount.items():
		frappe.db.sql("""update `tabSales Taxes and Charges`
			set tax_amount_after_discount_amount = tax_amount
			where parenttype = %s and parent not in (%s)""" %
			('%s', ', '.join(['%s']*(len(discounted_records)+1))),
			tuple([dt, ''] + discounted_records))
