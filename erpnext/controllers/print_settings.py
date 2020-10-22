# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

def print_settings_for_item_table(doc, settings=None):
	doc.print_templates = {
		"qty": "templates/print_formats/includes/item_table_qty.html"
	}
	doc.hide_in_print_layout = ["uom", "stock_uom"]

	setting_fields = ['compact_item_print', 'print_uom_after_quantity']
	set_doc_flags_from_settings(doc, setting_fields, settings)

	if doc.flags.compact_item_print:
		doc.print_templates["description"] = "templates/print_formats/includes/item_table_description.html"
		doc.flags.compact_item_fields = ["description", "qty", "rate", "amount"]
		doc.flags.format_columns = format_columns

def print_settings_for_taxes(doc, settings=None):

	set_doc_flags_from_settings(doc, ['print_taxes_with_zero_amount'], settings)

	doc.flags.show_inclusive_tax_in_print = doc.is_inclusive_tax()

	doc.print_templates = {
		"total": "templates/print_formats/includes/total.html",
		"taxes": "templates/print_formats/includes/taxes.html"
	}

def set_doc_flags_from_settings(doc, fields, settings=None):
	if not settings: settings = {}

	print_settings = frappe.get_single('Print Settings')

	for field in fields:
		if field in settings:
			doc.flags[field] = settings.get(field)
		else:
			doc.flags[field] = print_settings.get(field)

def format_columns(display_columns, compact_fields):
	compact_fields = compact_fields + ["image", "item_code", "item_name"]
	final_columns = []
	for column in display_columns:
		if column not in compact_fields:
			final_columns.append(column)
	return final_columns

def has_items_field(doc):
	meta = frappe.get_meta(doc.doctype)
	items_field = meta.get_field('items')
	if items_field and items_field.fieldtype == 'Table':
		return True
	return False

def has_taxes_field(doc):
	meta = frappe.get_meta(doc.doctype)
	taxes_field = meta.get_field('taxes')
	if taxes_field and taxes_field.fieldtype == 'Table':
		return True
	return False

def get_print_settings():
	settings = {
		'compact_item_print': {
			'condition': 'erpnext.controllers.print_settings.has_items_field',
			'fieldtype': 'Check',
			'child_field': 'items',
			'label': 'Compact Item Print',
			'set_template': 'erpnext.controllers.print_settings.print_settings_for_item_table'
		},
		'print_uom_after_quantity': {
			'condition': 'erpnext.controllers.print_settings.has_taxes_field',
			'fieldtype': 'Check',
			'child_field': 'items',
			'label': 'Print UOM after Quantity',
			'set_template': 'erpnext.controllers.print_settings.print_settings_for_item_table'
		},
		'print_taxes_with_zero_amount': {
			'condition': 'erpnext.controllers.print_settings.has_taxes_field',
			'fieldtype': 'Check',
			'label': 'Print taxes with zero amount',
			'set_template': 'erpnext.controllers.print_settings.print_settings_for_taxes'
		}
	}

	return settings
