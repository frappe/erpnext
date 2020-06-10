# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.meta import get_field_precision

def execute():
	if not frappe.db.sql("""select name from `tabPatch Log`
		where patch = 'erpnext.patches.v5_0.taxes_and_totals_in_party_currency'"""):
			return
	selling_doctypes = ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]
	buying_doctypes = ["Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"]

	for dt in selling_doctypes:
		update_values(dt, "Sales Taxes and Charges")

	for dt in buying_doctypes:
		update_values(dt, "Purchase Taxes and Charges")

def update_values(dt, tax_table):
	rate_field_precision = get_field_precision(frappe.get_meta(dt + " Item").get_field("rate"))
	tax_amount_precision = get_field_precision(frappe.get_meta(tax_table).get_field("tax_amount"))

	# update net_total, discount_on
	frappe.db.sql("""
		UPDATE
			`tab{0}`
		SET
			total_taxes_and_charges = round(base_total_taxes_and_charges / conversion_rate, {1})
		WHERE
			docstatus < 2
			and ifnull(base_total_taxes_and_charges, 0) != 0
			and ifnull(total_taxes_and_charges, 0) = 0
	""".format(dt, tax_amount_precision))

	# update net_amount
	frappe.db.sql("""
		UPDATE
			`tab{0}` par, `tab{1}` item
		SET
			item.net_amount = round(item.base_net_amount / par.conversion_rate, {2}),
			item.net_rate = round(item.base_net_rate / par.conversion_rate, {2})
		WHERE
			par.name = item.parent
			and par.docstatus < 2
			and ((ifnull(item.base_net_amount, 0) != 0 and ifnull(item.net_amount, 0) = 0)
				or (ifnull(item.base_net_rate, 0) != 0 and ifnull(item.net_rate, 0) = 0))
	""".format(dt, dt + " Item", rate_field_precision))

	# update tax in party currency
	frappe.db.sql("""
		UPDATE
			`tab{0}` par, `tab{1}` tax
		SET
			tax.tax_amount = round(tax.base_tax_amount / par.conversion_rate, {2}),
			tax.total = round(tax.base_total / conversion_rate, {2}),
			tax.tax_amount_after_discount_amount = round(tax.base_tax_amount_after_discount_amount / conversion_rate, {2})
		WHERE
			par.name = tax.parent
			and par.docstatus < 2
			and ((ifnull(tax.base_tax_amount, 0) != 0 and  ifnull(tax.tax_amount, 0) = 0)
				or (ifnull(tax.base_total, 0) != 0 and ifnull(tax.total, 0) = 0)
				or (ifnull(tax.base_tax_amount_after_discount_amount, 0) != 0 and
					ifnull(tax.tax_amount_after_discount_amount, 0) = 0))
	""".format(dt, tax_table, tax_amount_precision))