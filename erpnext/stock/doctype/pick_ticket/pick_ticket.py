# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PickTicket(Document):
	def set_item_locations(self):
		reference_items = self.reference_document_items
		self.delete_key('items')
		for item in reference_items:
			data = get_items_with_warehouse_and_quantity(item)

			for item_info in data:
				print(self.append('items', item_info))

		for item_doc in self.get('items'):
			if frappe.get_cached_value('Item', item_doc.item, 'has_serial_no'):
				set_serial_nos(item_doc)
			elif frappe.get_cached_value('Item', item_doc.item, 'has_batch_no'):
				set_batch_no(item_doc, self)

def get_available_items(item):
	# gets all items available in different warehouses
	# FIFO
	available_items = frappe.get_all('Bin', filters={
		'item_code': item,
		'actual_qty': ['>', 0]
	}, fields=['warehouse', 'actual_qty as qty'], order_by='creation')

	return available_items

def get_items_with_warehouse_and_quantity(item_doc):
	items = []
	item_locations = get_available_items(item_doc.item)
	remaining_qty = item_doc.qty


	while remaining_qty > 0 and item_locations:
		item_location = item_locations.pop(0)
		qty = remaining_qty if item_location.qty >= remaining_qty else item_location.qty
		items.append({
			'item': item_doc.item,
			'qty': qty,
			'warehouse': item_location.warehouse,
			'reference_doctype': item_doc.reference_doctype,
			'reference_name': item_doc.reference_name
		})
		remaining_qty -= qty

	if remaining_qty:
		print('---------- {} qty of {} is out of stock. Skipping... -------------'.format(remaining_qty, item_doc.item))
		return items

	return items

def set_serial_nos(item_doc):
	serial_nos = frappe.get_all('Serial No', {
		'item_code': item_doc.item,
		'warehouse': item_doc.warehouse
	}, limit=item_doc.qty, order_by='purchase_date')
	item_doc.set('serial_no', '\n'.join([serial_no.name for serial_no in serial_nos]))

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
		if batch_expiry and batch_expiry < frappe.utils.getdate():
			print('---------- Batch {} is expired. Skipping... -------------'.format(batch.batch_no))
			continue
		item_doc.batch_no = batch.batch_no
		required_qty -= batch.qty
		if batch.qty >= item_doc.qty:
			break
		else:
			# split item if quantity of item in batch is less that required
			# Look for another batch

			# set quantity of of item equal to batch quantity
			item_doc.set('qty', batch.qty)
			item_doc = parent_doc.append('items', {
				'item': item_doc.item,
				'qty': required_qty,
				'warehouse': item_doc.warehouse,
				'reference_doctype': item_doc.reference_doctype,
				'reference_name': item_doc.reference_name
			})
	if required_qty:
		print('---------- No batches found for {} qty of {}. Skipping... -------------'.format(required_qty, item_doc.item))
		parent_doc.remove(item_doc)
