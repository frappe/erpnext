# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class PickTicket(Document):
	def set_item_locations(self):
		reference_items = self.reference_items

		from_warehouses = None
		if self.parent_warehouse:
			from_warehouses = frappe.db.get_descendants('Warehouse', self.parent_warehouse)

		# Reset
		self.delete_key('item_locations')
		for item in reference_items:
			data = get_items_with_warehouse_and_quantity(item, from_warehouses)
			for item_info in data:
				print(self.append('item_locations', item_info))

		for item_doc in self.get('item_locations'):
			if frappe.get_cached_value('Item', item_doc.item, 'has_serial_no'):
				set_serial_nos(item_doc)
			elif frappe.get_cached_value('Item', item_doc.item, 'has_batch_no'):
				set_batch_no(item_doc, self)

def get_items_with_warehouse_and_quantity(item_doc, from_warehouses):
	items = []
	item_locations = get_available_items(item_doc.item, from_warehouses)
	remaining_qty = item_doc.qty

	while remaining_qty > 0 and item_locations:
		item_location = item_locations.pop(0)
		qty = remaining_qty if item_location.qty >= remaining_qty else item_location.qty
		items.append({
			'item': item_doc.item,
			'qty': qty,
			'warehouse': item_location.warehouse,
			'reference_doctype': item_doc.reference_doctype,
			'reference_name': item_doc.reference_name,
			'reference_document_item': item_doc.reference_document_item,
		})
		remaining_qty -= qty

	if remaining_qty:
		frappe.msgprint('{} qty of {} is out of stock. Skipping...'.format(remaining_qty, item_doc.item))
		return items

	return items

def get_available_items(item, from_warehouses):
	# gets all items available in different warehouses
	# FIFO
	filters = frappe._dict({
		'item_code': item,
		'actual_qty': ['>', 0]
	})
	if from_warehouses:
		filters.warehouse = ['in', from_warehouses]

	available_items = frappe.get_all('Bin',
		fields=['warehouse', 'actual_qty as qty'],
		filters=filters,
		order_by='creation')

	return available_items

def set_serial_nos(item_doc):
	serial_nos = frappe.get_all('Serial No', {
		'item_code': item_doc.item,
		'warehouse': item_doc.warehouse
	}, limit=item_doc.qty, order_by='purchase_date')
	item_doc.set('serial_no', '\n'.join([serial_no.name for serial_no in serial_nos]))

	# should we assume that all serialized item available in stock will have serial no?

def set_batch_no(item_doc, parent_doc):
	batches = frappe.db.sql("""
		SELECT
			`batch_no`,
			SUM(`actual_qty`) AS `qty`
		FROM
			`tabStock Ledger Entry`
		WHERE
			`item_code`=%(item_code)s
			AND `warehouse`=%(warehouse)s
		GROUP BY
			`warehouse`,
			`batch_no`,
			`item_code`
		HAVING `qty` > 0
	""", {
		'item_code': item_doc.item,
		'warehouse': item_doc.warehouse,
	}, as_dict=1)
	print(batches)

	required_qty = item_doc.qty
	while required_qty > 0 and batches:
		batch = batches.pop()
		batch_expiry = frappe.get_value('Batch', batch.batch_no, 'expiry_date')
		if batch_expiry and batch_expiry <= frappe.utils.getdate():
			frappe.msgprint('Skipping expired Batch {}'.format(batch.batch_no))
			continue
		item_doc.batch_no = batch.batch_no
		if batch.qty >= item_doc.qty:
			required_qty = 0
			break
		else:
			# split item if quantity of item in batch is less that required
			# Look for another batch

			# set quantity of of item equal to batch quantity
			required_qty -= batch.qty
			item_doc.set('qty', batch.qty)
			item_doc = parent_doc.append('items', {
				'item': item_doc.item,
				'qty': required_qty,
				'warehouse': item_doc.warehouse,
				'reference_doctype': item_doc.reference_doctype,
				'reference_name': item_doc.reference_name,
				'reference_document_item': item_doc.reference_document_item,
			})
	if required_qty:
		frappe.msgprint('No batches found for {} qty of {}. Skipping...'.format(required_qty, item_doc.item))
		parent_doc.remove(item_doc)

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
	target_doc = get_mapped_doc("Pick Ticket", source_name, {
		"Pick Ticket": {
			"doctype": "Delivery Note",
			# "validation": {
			# 	"docstatus": ["=", 1]
			# }
		},
		"Pick Ticket Item": {
			"doctype": "Delivery Note Item",
			"field_map": {
				"item": "item_code",
				"reference_docname": "against_sales_order",
			},
		},
	}, target_doc)

	return target_doc