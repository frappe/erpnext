# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import cstr

def execute():
	frappe.reload_doc("setup", "doctype", "item_source")

	to_create = []

	item_meta = frappe.get_meta("Item")
	item_source_df = item_meta.get_field('item_source')
	if item_source_df:
		df_item_sources = cstr(item_source_df.options)
		df_item_sources = df_item_sources.split('\n')
		to_create += df_item_sources

	db_item_sources = frappe.db.sql_list("select distinct item_source from tabItem")
	to_create += db_item_sources

	to_create = list(set([d for d in to_create if d]))

	for name in to_create:
		if not frappe.db.exists("Item Source", name):
			doc = frappe.new_doc("Item Source")
			doc.item_source_name = name
			doc.save()

	frappe.delete_doc_if_exists("Property Setter", "Item-item_source-options")
	frappe.delete_doc_if_exists("Property Setter", "Item-item_source-fieldtype")
