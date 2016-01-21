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
	customised_print_preview = cint(frappe.db.get_value("Stock Settings", None, "customised_print_preview"))
	
	if customised_print_preview:
		doc.hide_in_print_layout = ["item_code", "item_name", "image", "uom", "stock_uom", "price_list_rate","serial_no","discount_percentage","schedule_date", "supplier_part_no"]
	else:
		doc.hide_in_print_layout = ["item_code", "item_name", "image", "uom", "stock_uom"]

