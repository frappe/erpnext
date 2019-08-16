# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from six import iteritems
from frappe.model.mapper import get_mapped_doc, map_child_doc
from frappe.utils import floor, flt, today
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as make_delivery_note_from_sales_order

class PickList(Document):
	def set_item_locations(self):
		reference_items = self.reference_items

		from_warehouses = None
		if self.parent_warehouse:
			from_warehouses = frappe.db.get_descendants('Warehouse', self.parent_warehouse)

		# Reset
		self.delete_key('item_locations')
		for item_doc in reference_items:
			if frappe.get_cached_value('Item', item_doc.item_code, 'has_serial_no'):
				item_locations = get_item_locations_based_on_serial_nos(item_doc)
			elif frappe.get_cached_value('Item', item_doc.item_code, 'has_batch_no'):
				item_locations = get_item_locations_based_on_batch_nos(item_doc)
			else:
				item_locations = get_items_with_warehouse_and_quantity(item_doc, from_warehouses)

			for row in item_locations:
				row.update({
					'item_code': item_doc.item_code,
					'sales_order': item_doc.sales_order,
					'sales_order_item': item_doc.sales_order_item,
					'uom': item_doc.uom,
					'stock_uom': item_doc.stock_uom,
					'conversion_factor': item_doc.conversion_factor,
					'stock_qty': row.get("qty", 0) * item_doc.conversion_factor,
					'picked_qty': row.get("qty", 0) * item_doc.conversion_factor
				})
				self.append('item_locations', row)

def get_items_with_warehouse_and_quantity(item_doc, from_warehouses):
	item_locations = []
	item_location_map = get_available_items(item_doc.item_code, from_warehouses)
	remaining_stock_qty = item_doc.stock_qty
	while remaining_stock_qty > 0 and item_location_map:
		item_location = item_location_map.pop(0)
		stock_qty = remaining_stock_qty if item_location.qty >= remaining_stock_qty else item_location.qty
		qty = stock_qty / (item_doc.conversion_factor or 1)

		uom_must_be_whole_number = frappe.db.get_value("UOM", item_doc.uom, "must_be_whole_number")
		if uom_must_be_whole_number:
			qty = floor(qty)
			stock_qty = qty * item_doc.conversion_factor

		item_locations.append({
			'qty': qty,
			'warehouse': item_location.warehouse
		})
		remaining_stock_qty -= stock_qty

	if remaining_stock_qty:
		frappe.msgprint('{0} {1} of {2} is not available.'
			.format(remaining_stock_qty / item_doc.conversion_factor, item_doc.uom, item_doc.item_code))
	return item_locations

def get_available_items(item_code, from_warehouses):
	# gets all items available in different warehouses
	filters = frappe._dict({
		'item_code': item_code,
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
		'item_code': item_doc.item_code,
		'warehouse': item_doc.warehouse
	}, limit=item_doc.stock_qty, order_by='purchase_date')
	item_doc.set('serial_no', '\n'.join([serial_no.name for serial_no in serial_nos]))

	# should we assume that all serialized item_code available in stock will have serial no?

def get_item_locations_based_on_serial_nos(item_doc):
	serial_nos = frappe.get_all('Serial No',
		fields = ['name', 'warehouse'],
		filters = {
			'item_code': item_doc.item_code,
			'warehouse': ['!=', '']
		}, limit=item_doc.stock_qty, order_by='purchase_date', as_list=1)

	remaining_stock_qty = flt(item_doc.stock_qty) - len(serial_nos)
	if remaining_stock_qty:
		frappe.msgprint('{0} {1} of {2} is not available.'
			.format(remaining_stock_qty, item_doc.stock_uom, item_doc.item_code))

	warehouse_serial_nos_map = frappe._dict()
	for serial_no, warehouse in serial_nos:
		warehouse_serial_nos_map.setdefault(warehouse, []).append(serial_no)

	item_locations = []
	for warehouse, serial_nos in iteritems(warehouse_serial_nos_map):
		item_locations.append({
			'qty': len(serial_nos),
			'warehouse': warehouse,
			'serial_no': '\n'.join(serial_nos)
		})

	return item_locations

def get_item_locations_based_on_batch_nos(item_doc):
	batch_qty = frappe.db.sql("""
		SELECT
			sle.`warehouse`,
			sle.`batch_no`,
			SUM(sle.`actual_qty`) AS `qty`
		FROM
			`tabStock Ledger Entry` sle, `tabBatch` batch
		WHERE
			sle.batch_no = batch.name
			and sle.`item_code`=%(item_code)s
			and IFNULL(batch.expiry_date, '2200-01-01') > %(today)s
		GROUP BY
			`warehouse`,
			`batch_no`,
			`item_code`
		HAVING `qty` > 0
		ORDER BY IFNULL(batch.expiry_date, '2200-01-01')
	""", {
		'item_code': item_doc.item_code,
		'today': today()
	}, as_dict=1)

	item_locations = []
	required_qty = item_doc.qty
	for d in batch_qty:
		if d.qty > required_qty:
			d.qty = required_qty
		else:
			required_qty -= d.qty

		item_locations.append(d)

		if required_qty <= 0:
			break

	# required_qty = item_doc.qty
	# while required_qty > 0 and batches:
	# 	batch = batches.pop()
	# 	batch_expiry = frappe.get_value('Batch', batch.batch_no, 'expiry_date')
	# 	if batch_expiry and batch_expiry <= frappe.utils.getdate():
	# 		frappe.msgprint('Skipping expired Batch {}'.format(batch.batch_no))
	# 		continue
	# 	item_doc.batch_no = batch.batch_no
	# 	if batch.qty >= item_doc.qty:
	# 		required_qty = 0
	# 		break
	# 	else:
	# 		# split item_code if quantity of item_code in batch is less that required
	# 		# Look for another batch

	# 		required_qty -= batch.qty
	# 		# set quantity of current item_code equal to batch quantity
	# 		item_doc.set('qty', batch.qty)
	# 		item_doc = parent_doc.append('items', {
	# 			'item_code': item_doc.item_code,
	# 			'qty': required_qty,
	# 			'warehouse': item_doc.warehouse,
	# 			'sales_order': item_doc.sales_order,
	# 			'sales_order_item': item_doc.sales_order_item,
	# 			'uom': item_doc.uom,
	# 			'stock_uom': item_doc.stock_uom,
	# 			'conversion_factor': item_doc.conversion_factor,
	# 			'stock_qty': qty * item_doc.conversion_factor,
	# 		})

	if required_qty:
		frappe.msgprint('No batches found for {} qty of {}.'.format(required_qty, item_doc.item_code))

	return item_locations

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
	pick_list = frappe.get_doc('Pick List', source_name)
	sales_orders = [d.sales_order for d in pick_list.item_locations]
	sales_orders = set(sales_orders)

	delivery_note = None
	for sales_order in sales_orders:
		delivery_note = make_delivery_note_from_sales_order(sales_order,
			delivery_note, skip_item_mapping=True)

	for location in pick_list.item_locations:
		sales_order_item = frappe.get_cached_doc('Sales Order Item', location.sales_order_item)
		item_table_mapper = {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_sales_order",
			},
			"condition": lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
		}

		dn_item = map_child_doc(sales_order_item, delivery_note, item_table_mapper)

		if dn_item:
			dn_item.warehouse = location.warehouse
			dn_item.qty = location.qty

			update_delivery_note_item(sales_order_item, dn_item, delivery_note)

	set_delivery_note_missing_values(delivery_note)

	return delivery_note


def set_delivery_note_missing_values(target):
	target.run_method("set_missing_values")
	target.run_method("set_po_nos")
	target.run_method("calculate_taxes_and_totals")

def update_delivery_note_item(source, target, delivery_note):
	cost_center = frappe.db.get_value("Project", delivery_note.project, "cost_center")
	if not cost_center:
		cost_center = frappe.db.get_value('Item Default',
			fieldname=['buying_cost_center'],
			filters={
				'parent': source.item_code,
				'parenttype': 'Item',
				'company': delivery_note.company
			})

	if not cost_center:
		cost_center = frappe.db.get_value('Item Default',
			fieldname=['buying_cost_center'],
			filters={
				'parent': source.item_group,
				'parenttype': 'Item Group',
				'company': delivery_note.company
			})

	target.cost_center = cost_center