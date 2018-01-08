# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class ItemAlternative(Document):
	def onload(self):

		# Set cache for self.item UOMs Detail list
		if not self.get("__islocal"):
			uoms = frappe.get_all('UOM Conversion Detail',
								  filters={'parent': self.item},
								  fields=['*'])
			self.set_onload('self_uoms', uoms)
		else:
			self.set_onload('self_uoms', {})

	def on_trash(self):
		# Delete related Two-Ways connections.
		if self.alt_items:
			for item in self.alt_items:
				delete_two_way(item.item, self.item)


@frappe.whitelist()
def check_one_way(cur_alt_item, parent_item):
	"""
		Insanity check for One-Way Relation, checking if user enters a One-Way
		relation to an obj that has already Two-Way relation
		params:cur_alt_item:hash
			Child Table current row Item
		params:parent_item:hash
			Doctype item field
	"""
	doc = frappe.get_all('Item Alternative', filters={'item': cur_alt_item})
	if doc:
		doc = frappe.get_doc('Item Alternative', doc[0]['name'])
		if doc.alt_items:
			for alt_item in doc.alt_items:
				if alt_item.item == parent_item:
					if alt_item.type == _("Two-Way"):
						# Remove keyword is neccesary for on-the fly validation
						return "Remove"
	return


@frappe.whitelist()
def check_two_way(cur_alt_item, cur_item_uom, parent_item, parent_uom):
	"""
		Checking Two-Way relation and creating the relation if needed.
		params:cur_alt_item:hash
			Child Table current row Item
		params:cur_item_uom:hash:
			Child Table current row UOM Detail
		params:parent_uom:hash
			Doctype item field UOM Detail
		params:parent_item:hash
			Doctype item field
	"""
	doc = frappe.get_all('Item Alternative', filters={'item': cur_alt_item})
	if doc:
		doc = frappe.get_doc('Item Alternative', doc[0]['name'])
	else:
		doc = frappe.new_doc("Item Alternative")
		doc.item = cur_alt_item
		doc.alt_items = []

	already_set = False
	for alt_item in doc.alt_items:
		if alt_item.item == parent_item:
			if alt_item.type == _("Two-Way"):
				already_set = True
				frappe.msgprint(_("Relation Already Exists"), alert=True)
	if not already_set:
		puom = frappe.get_doc('UOM Conversion Detail', parent_uom)
		cuom = frappe.get_doc('UOM Conversion Detail', cur_item_uom)
		new_doc = frappe.new_doc('Item Alternative')
		new_doc.parent = doc.name
		new_doc.parenttype = 'Item Alternative'
		new_doc.parentfield = 'alt_items'
		new_doc.item = parent_item
		new_doc.item_name = frappe.get_doc('Item', parent_item).item_name
		new_doc.uom = parent_uom
		new_doc.uom_display = str(puom.uom)+ " ~ " + str(puom.conversion_factor)
		new_doc.type = _("Two-Way")
		new_doc.parent_uom = cur_item_uom
		new_doc.parent_uom_display = str(cuom.uom)+ " ~ " + str(cuom.conversion_factor)
		doc.alt_items.append(new_doc)
		frappe.msgprint(_("Two-Way Relation Created"), alert=True)
	doc.save()
	frappe.db.commit()
	return

@frappe.whitelist()
def delete_two_way(deleted_item, parent_item):
	"""
		Deleting Two-Way if any on parent child tables user deletes row
		params:deleted_item:hash
			Child Table deleted row Item
		params:parent_item:hash
			Doctype item field
	"""
	parent = frappe.get_all('Item Alternative', filters={'item': deleted_item})
	if parent:
		parent = parent[0].name
		frappe.db.sql("""delete from `tabAlternative List`
					 where parent=%s and item=%s
					 """, (parent, parent_item))
		frappe.db.commit()
		frappe.msgprint(_("Deleted Related Two-Way Relation"), alert=True)
	return
