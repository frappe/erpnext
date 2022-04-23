# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for document in ["bom", "bom_item", "bom_explosion_item"]:
		frappe.reload_doc('manufacturing', 'doctype', document)

	frappe.db.sql(" update `tabBOM` set bom_level = 0 where docstatus = 1")

	bom_list = frappe.db.sql_list("""select name from `tabBOM` bom
		where docstatus=1 and is_active=1 and not exists(select bom_no from `tabBOM Item`
		where parent=bom.name and ifnull(bom_no, '')!='')""")

	count = 0
	while(count < len(bom_list)):
		for parent_bom in get_parent_boms(bom_list[count]):
			bom_doc = frappe.get_cached_doc("BOM", parent_bom)
			bom_doc.set_bom_level(update=True)
			bom_list.append(parent_bom)
		count += 1

def get_parent_boms(bom_no):
	return frappe.db.sql_list("""
		select distinct bom_item.parent from `tabBOM Item` bom_item
		where bom_item.bom_no = %s and bom_item.docstatus=1 and bom_item.parenttype='BOM'
			and exists(select bom.name from `tabBOM` bom where bom.name=bom_item.parent and bom.is_active=1)
	""", bom_no)
