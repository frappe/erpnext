# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PickTicket(Document):
	pass

def get_pick_list(reference_doctype, reference_name, items_field):
	doc = frappe.new_doc('Pick Ticket')
	reference_doc = frappe.get_doc(reference_doctype, reference_name)
	doc.company = reference_doc.company
	items = reference_doc.get(items_field)

	add_picklist_items(items, doc, reference_doc)

	doc.insert()

	return doc

def get_available_items(item):
	# gets all items available in different warehouses
	# FIFO
	available_items = frappe.get_all('Bin', filters={
		'item_code': item,
		'actual_qty': ['>', 0]
	}, fields=['warehouse', 'actual_qty as qty'], order_by='creation')

	return available_items

def get_items_with_warehouse_and_quantity(item_doc, reference_doc):
	items = []
	item_locations = get_available_items(item_doc.item_code)
	if not item_locations: return items

	remaining_qty = item_doc.qty

	while remaining_qty > 0 and item_locations:
		item_location = item_locations.pop(0)
		qty = remaining_qty if item_location.qty >= remaining_qty else item_location.qty
		items.append({
			'item': item_doc.item_code,
			'qty': qty,
			'warehouse': item_location.warehouse,
			'reference_doctype': reference_doc.doctype,
			'reference_name': reference_doc.name
		})
		remaining_qty -= qty

	return items

def add_picklist_items(reference_items, doc, reference_doc):
	for item in reference_items:
		data = get_items_with_warehouse_and_quantity(item, reference_doc)

		for item_info in data:
			doc.append('items', item_info)

	for item in doc.get('items'):
		if item.has_serial_no:
			serial_nos = frappe.get_all('Serial No', {
				'item_code': item.item,
				'warehouse': item.warehouse
			}, limit=item.qty, order_by='purchase_date')
			item.serial_no = '\n'.join([serial_no.name for serial_no in serial_nos])

		# if item.has_batch_no:
		# 	serial_nos = frappe.get_all('Batch', {
		# 		'item_code': item.item,
		# 		'warehouse': item.warehouse
		# 	}, limit=item.qty, order_by='purchase_date')
		# 	item.serial_no = '\n'.join([serial_no.name for serial_no in serial_nos])