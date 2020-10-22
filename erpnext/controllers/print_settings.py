# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

def print_settings_for_item_table(doc, setting_value=None):

	doc.print_templates = {
		"qty": "templates/print_formats/includes/item_table_qty.html"
	}
	doc.hide_in_print_layout = ["uom", "stock_uom"]

	doc.flags.compact_item_print = setting_value if setting_value is not None\
		else cint(frappe.db.get_single_value("Print Settings", "compact_item_print"))

	if doc.flags.compact_item_print:
		doc.print_templates["description"] = "templates/print_formats/includes/item_table_description.html"
		doc.flags.compact_item_fields = ["description", "qty", "rate", "amount"]
		doc.flags.format_columns = format_columns

def print_settings_for_taxes(doc, setting_value=None):
	doc.flags.print_taxes_with_zero_amount = setting_value if setting_value is not None\
		else cint(frappe.db.get_single_value("Print Settings", "print_taxes_with_zero_amount"))
	doc.flags.show_inclusive_tax_in_print = doc.is_inclusive_tax()

	doc.print_templates = {
		"total": "templates/print_formats/includes/total.html",
		"taxes": "templates/print_formats/includes/taxes.html"
	}

def format_columns(display_columns, compact_fields):
	compact_fields = compact_fields + ["image", "item_code", "item_name"]
	final_columns = []
	for column in display_columns:
		if column not in compact_fields:
			final_columns.append(column)
	return final_columns

@frappe.whitelist()
def show_compact_item_setting(doc):
	meta = frappe.get_meta(doc.doctype)
	items_field = meta.get_field('items')
	if items_field and items_field.fieldtype == 'Table':
		return True
	return False

@frappe.whitelist()
def show_taxes_setting(doc):
	meta = frappe.get_meta(doc.doctype)
	items_field = meta.get_field('taxes')
	if items_field and items_field.fieldtype == 'Table':
		return True
	return False

def get_print_settings():
	settings = {
		'compact_item_print': {
			'condition': 'erpnext.controllers.print_settings.show_compact_item_setting',
			'fieldtype': 'Check',
			'child_field': 'items',
			'label': 'Compact Item Print',
			'set_template': 'erpnext.controllers.print_settings.print_settings_for_item_table'
		},
		'print_taxes_with_zero_amount': {
			'condition': 'erpnext.controllers.print_settings.show_taxes_setting',
			'fieldtype': 'Check',
			'label': 'Print taxes with zero amount',
			'set_template': 'erpnext.controllers.print_settings.print_settings_for_taxes'
		}
	}

	return settings
