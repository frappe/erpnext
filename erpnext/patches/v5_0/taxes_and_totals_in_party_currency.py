
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

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

	# update net_total, discount_on
	frappe.db.sql("""
		UPDATE
			`tab{0}`
		SET
			total = net_total,
			base_total = net_total*conversion_rate,
			net_total = base_net_total / conversion_rate,
			apply_discount_on = "Grand Total"
		WHERE
			docstatus < 2
	""".format(dt))


	# update net_amount
	frappe.db.sql("""
		UPDATE
			`tab{0}` par, `tab{1}` item
		SET
			item.base_net_amount = item.base_amount,
			item.base_net_rate = item.base_rate,
			item.net_amount = item.base_net_amount / par.conversion_rate,
			item.net_rate = item.base_net_rate / par.conversion_rate,
			item.base_amount = item.amount * par.conversion_rate,
			item.base_rate = item.rate * par.conversion_rate
		WHERE
			par.name = item.parent
			and par.docstatus < 2
	""".format(dt, dt + " Item"))

	# update tax in party currency
	frappe.db.sql("""
		UPDATE
			`tab{0}` par, `tab{1}` tax
		SET
			tax.base_tax_amount = tax.tax_amount,
			tax.tax_amount = tax.base_tax_amount / par.conversion_rate,
			tax.base_total = tax.total,
			tax.total = tax.base_total / conversion_rate,
			tax.base_tax_amount_after_discount_amount = tax.tax_amount_after_discount_amount,
			tax.tax_amount_after_discount_amount = tax.base_tax_amount_after_discount_amount / conversion_rate
		WHERE
			par.name = tax.parent
			and par.docstatus < 2
	""".format(dt, tax_table))
