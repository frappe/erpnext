# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "tax_rule")

	customers = frappe.db.sql("""select name, default_taxes_and_charges from tabCustomer where
		ifnull(default_taxes_and_charges, '') != '' """, as_dict=1)

	for d in customers:
		if not frappe.db.sql("select name from `tabTax Rule` where customer=%s", d.name):
			tr = frappe.new_doc("Tax Rule")
			tr.tax_type = "Sales"
			tr.customer = d.name
			tr.sales_tax_template = d.default_taxes_and_charges
			tr.save()


	suppliers = frappe.db.sql("""select name, default_taxes_and_charges from tabSupplier where
		ifnull(default_taxes_and_charges, '') != '' """, as_dict=1)

	for d in suppliers:
		if not frappe.db.sql("select name from `tabTax Rule` where supplier=%s", d.name):
			tr = frappe.new_doc("Tax Rule")
			tr.tax_type = "Purchase"
			tr.supplier = d.name
			tr.purchase_tax_template = d.default_taxes_and_charges
			tr.save()