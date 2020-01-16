# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import re

def execute():
	# NOTE: sequence is important
	fields_list = (
		("amount", "base_amount"),
		("ref_rate", "price_list_rate"),
		("base_ref_rate", "base_price_list_rate"),
		("adj_rate", "discount_percentage"),
		("export_rate", "rate"),
		("basic_rate", "base_rate"),
		("export_amount", "amount"),
		("reserved_warehouse", "warehouse"),
		("import_ref_rate", "price_list_rate"),
		("purchase_ref_rate", "base_price_list_rate"),
		("discount_rate", "discount_percentage"),
		("import_rate", "rate"),
		("purchase_rate", "base_rate"),
		("import_amount", "amount")
	)

	condition = " or ".join("""html like "%%{}%%" """.format(d[0].replace("_", "\\_")) for d in fields_list
		if d[0] != "amount")

	for name, html in frappe.db.sql("""select name, html from `tabPrint Format`
		where standard = 'No' and ({}) and html not like '%%frappe.%%'""".format(condition)):
			html = html.replace("wn.", "frappe.")
			for from_field, to_field in fields_list:
				html = re.sub(r"\b{}\b".format(from_field), to_field, html)

			frappe.db.set_value("Print Format", name, "html", html)
