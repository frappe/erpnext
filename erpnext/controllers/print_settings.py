# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

def print_settings_for_item_table(doc):

	doc.print_templates = {
		"qty": "templates/print_formats/includes/item_table_qty.html"
	}
	doc.hide_in_print_layout = ["uom", "stock_uom"]

	doc.flags.compact_item_print = cint(frappe.db.get_value("Print Settings", None, "compact_item_print"))

	if doc.flags.compact_item_print:
		doc.print_templates["description"] = "templates/print_formats/includes/item_table_description.html"
		doc.hide_in_print_layout += ["item_code", "item_name", "image"]

		doc.flags.compact_item_fields = ["description", "qty", "rate", "amount"]
		doc.flags.show_in_description = []

		for df in doc.meta.fields:
			if df.fieldtype not in ("Section Break", "Column Break", "Button"):
				if not doc.is_print_hide(df.fieldname):
					if df.fieldname not in doc.hide_in_print_layout and df.fieldname not in doc.flags.compact_item_fields:
						doc.hide_in_print_layout.append(df.fieldname)
						doc.flags.show_in_description.append(df.fieldname)
