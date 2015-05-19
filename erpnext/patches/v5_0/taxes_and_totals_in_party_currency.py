
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model.meta import get_field_precision
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def execute():
	selling_doctypes = ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]
	buying_doctypes = ["Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"]

	for dt in selling_doctypes:
		update_values(dt, "Sales Taxes and Charges")

	for dt in buying_doctypes:
		update_values(dt, "Purchase Taxes and Charges")

def update_values(dt, tax_table):
	frappe.reload_doctype(dt)
	frappe.reload_doctype(dt + " Item")
	frappe.reload_doctype(tax_table)
	
	net_total_precision = get_field_precision(frappe.get_meta(dt).get_field("net_total"))
	for field in ("total", "base_total", "base_net_total"):
		make_property_setter(dt, field, "precision", net_total_precision, "Select")
	
	rate_field_precision = get_field_precision(frappe.get_meta(dt + " Item").get_field("rate"))
	for field in ("net_rate", "base_net_rate", "net_amount", "base_net_amount", "base_rate", "base_amount"):
		make_property_setter(dt + " Item", field, "precision", rate_field_precision, "Select")
		
	tax_amount_precision = get_field_precision(frappe.get_meta(tax_table).get_field("tax_amount"))
	for field in ("base_tax_amount", "total", "base_total", "tax_amount_after_discount_amount", 
		"base_tax_amount_after_discount_amount"):
			make_property_setter(tax_table, field, "precision", tax_amount_precision, "Select")
	
	# update net_total, discount_on
	frappe.db.sql("""
		UPDATE
			`tab{0}`
		SET
			total = round(net_total, {1}),
			base_total = round(net_total*conversion_rate, {1}),
			net_total = round(base_net_total / conversion_rate, {1}),
			apply_discount_on = "Grand Total"
		WHERE
			docstatus < 2
	""".format(dt, net_total_precision))
	
	# update net_amount
	frappe.db.sql("""
		UPDATE
			`tab{0}` par, `tab{1}` item
		SET
			item.base_net_amount = round(item.base_amount, {2}),
			item.base_net_rate = round(item.base_rate, {2}),
			item.net_amount = round(item.base_amount / par.conversion_rate, {2}),
			item.net_rate = round(item.base_rate / par.conversion_rate, {2}),
			item.base_amount = round(item.amount * par.conversion_rate, {2}),
			item.base_rate = round(item.rate * par.conversion_rate, {2})
		WHERE
			par.name = item.parent
			and par.docstatus < 2
	""".format(dt, dt + " Item", rate_field_precision))

	# update tax in party currency
	frappe.db.sql("""
		UPDATE
			`tab{0}` par, `tab{1}` tax
		SET
			tax.base_tax_amount = round(tax.tax_amount, {2}),
			tax.tax_amount = round(tax.tax_amount / par.conversion_rate, {2}),
			tax.base_total = round(tax.total, {2}),
			tax.total = round(tax.total / conversion_rate, {2}),
			tax.base_tax_amount_after_discount_amount = round(tax.tax_amount_after_discount_amount, {2}),
			tax.tax_amount_after_discount_amount = round(tax.tax_amount_after_discount_amount / conversion_rate, {2})
		WHERE
			par.name = tax.parent
			and par.docstatus < 2
	""".format(dt, tax_table, tax_amount_precision))
