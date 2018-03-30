# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field
from frappe.modules import scrub, get_doctype_module

selling_doctypes = ("Quotation", "Sales Order", "Delivery Note", "Sales Invoice")

buying_doctypes = ("Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice")

selling_renamed_fields = (
	("net_total", "base_net_total"),
	("net_total_export", "net_total"),
	("other_charges_total", "base_total_taxes_and_charges"),
	("other_charges_total_export", "total_taxes_and_charges"),
	("grand_total", "base_grand_total"),
	("grand_total_export", "grand_total"),
	("rounded_total", "base_rounded_total"),
	("rounded_total_export", "rounded_total"),
	("in_words", "base_in_words"),
	("in_words_export", "in_words")
)

buying_renamed_fields = (
	("net_total", "base_net_total"),
	("net_total_import", "net_total"),
	("grand_total", "base_grand_total"),
	("grand_total_import", "grand_total"),
	("rounded_total", "base_rounded_total"),
	("in_words", "base_in_words"),
	("in_words_import", "in_words"),
	("other_charges_added", "base_taxes_and_charges_added"),
	("other_charges_added_import", "taxes_and_charges_added"),
	("other_charges_deducted", "base_taxes_and_charges_deducted"),
	("other_charges_deducted_import", "taxes_and_charges_deducted"),
	("total_tax", "base_total_taxes_and_charges")
)

def execute():
	for doctypes, fields in [[selling_doctypes, selling_renamed_fields], [buying_doctypes, buying_renamed_fields]]:
		for dt in doctypes:
			frappe.reload_doc(get_doctype_module(dt), "doctype", scrub(dt))
			table_columns = frappe.db.get_table_columns(dt)
			base_net_total = frappe.db.sql("select sum(ifnull({0}, 0)) from `tab{1}`".format(fields[0][1], dt))[0][0]
			if not base_net_total:
				for f in fields:
					if f[0] in table_columns:
						rename_field(dt, f[0], f[1])

				# Added new field "total_taxes_and_charges" in buying cycle, updating value
				if dt in ("Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"):
					frappe.db.sql("""update `tab{0}` set total_taxes_and_charges =
						round(base_total_taxes_and_charges/conversion_rate, 2)""".format(dt))
