# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

def print_settings_for_item_table(doc):
	
	doc.print_templates = {
		"description": "templates/print_formats/includes/item_table_description.html",
		"qty": "templates/print_formats/includes/item_table_qty.html"
	}
	customised_print_preview = cint(frappe.db.get_value("Features Setup", None, "customised_print_preview"))
	
	doc.hide_in_print_layout = ["item_code", "item_name", "image", "uom", "stock_uom"]

	std_fields = ["item_code", "item_name", "description", "qty", "rate", "amount", "stock_uom", "uom"] 

	if customised_print_preview:
		
		for df in doc.meta.fields:
			if df.fieldtype not in ("Section Break", "Column Break", "Button"):
				if not doc.is_print_hide(df.fieldname):
					if df.fieldname not in doc.hide_in_print_layout and df.fieldname not in std_fields:				
						doc.hide_in_print_layout.append(df.fieldname)


