# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from six import iteritems
from frappe.model.document import Document
from frappe import _
from frappe.utils import floor, flt, today
from frappe.model.mapper import get_mapped_doc, map_child_doc
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as create_delivery_note_from_sales_order

# TODO: Prioritize SO or WO group warehouse

class PickList(Document):
	def set_item_locations(self):
		item_locations = self.locations
		self.item_location_map = frappe._dict()

		from_warehouses = None
		if self.parent_warehouse:
			from_warehouses = frappe.db.get_descendants('Warehouse', self.parent_warehouse)

		# Reset
		self.delete_key('locations')
		for item_doc in item_locations:
			item_code = item_doc.item_code
			if frappe.get_cached_value('Item', item_code, 'has_serial_no'):
				locations = get_item_locations_based_on_serial_nos(item_doc)
			elif frappe.get_cached_value('Item', item_code, 'has_batch_no'):
				locations = get_item_locations_based_on_batch_nos(item_doc)
			else:
				if item_code not in self.item_location_map:
					self.item_location_map[item_code] = get_available_items(item_code, from_warehouses)
				locations = get_items_with_warehouse_and_quantity(item_doc, from_warehouses, self.item_location_map)

			# hack
			del item_doc.idx
			if len(locations) > 1:
				del item_doc.name

			for row in locations:
				stock_qty = row.get('qty', 0) * item_doc.conversion_factor
				row.update({
					'stock_qty': stock_qty,
					'picked_qty': stock_qty
				})

				location = item_doc
				location.update(row)
				self.append('locations', location)

def get_items_with_warehouse_and_quantity(item_doc, from_warehouses, item_location_map):
	available_locations = item_location_map.get(item_doc.item_code)
	locations = []
	skip_warehouse = None

	if item_doc.material_request:
		skip_warehouse = frappe.get_value('Material Request Item', item_doc.material_request_item, 'warehouse')

	remaining_stock_qty = item_doc.stock_qty
	while remaining_stock_qty > 0 and available_locations:
		item_location = available_locations.pop(0)

		stock_qty = remaining_stock_qty if item_location.qty >= remaining_stock_qty else item_location.qty
		qty = stock_qty / (item_doc.conversion_factor or 1)

		uom_must_be_whole_number = frappe.db.get_value('UOM', item_doc.uom, 'must_be_whole_number')
		if uom_must_be_whole_number:
			qty = floor(qty)
			stock_qty = qty * item_doc.conversion_factor
			if not stock_qty: break

		locations.append({
			'qty': qty,
			'warehouse': item_location.warehouse
		})
		remaining_stock_qty -= stock_qty

		qty_diff = item_location.qty - stock_qty
		# if extra quantity is available push current warehouse to available locations
		if qty_diff:
			item_location.qty = qty_diff
			available_locations = [item_location] + available_locations

	if remaining_stock_qty:
		frappe.msgprint('{0} {1} of {2} is not available.'
			.format(remaining_stock_qty / item_doc.conversion_factor, item_doc.uom, item_doc.item_code))

	# update available locations for the item
	item_location_map[item_doc.item_code] = available_locations
	return locations

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

	locations = []
	for warehouse, serial_nos in iteritems(warehouse_serial_nos_map):
		locations.append({
			'qty': len(serial_nos),
			'warehouse': warehouse,
			'serial_no': '\n'.join(serial_nos)
		})

	return locations

def get_item_locations_based_on_batch_nos(item_doc):
	batch_locations = frappe.db.sql("""
		SELECT
			sle.`warehouse`,
			sle.`batch_no`,
			SUM(sle.`actual_qty`) AS `qty`
		FROM
			`tabStock Ledger Entry` sle, `tabBatch` batch
		WHERE
			sle.batch_no = batch.name
			and sle.`item_code`=%(item_code)s
			and IFNULL(batch.`expiry_date`, '2200-01-01') > %(today)s
		GROUP BY
			`warehouse`,
			`batch_no`,
			`item_code`
		HAVING `qty` > 0
		ORDER BY IFNULL(batch.`expiry_date`, '2200-01-01'), batch.`creation`
	""", {
		'item_code': item_doc.item_code,
		'today': today()
	}, as_dict=1)

	locations = []
	required_qty = item_doc.stock_qty

	for batch_location in batch_locations:
		if batch_location.qty >= required_qty:
			# this batch should fulfill the required items
			batch_location.qty = required_qty
			required_qty = 0
		else:
			required_qty -= batch_location.qty

		locations.append(batch_location)

		if required_qty <= 0:
			break

	if required_qty:
		frappe.msgprint('No batches found for {} qty of {}.'.format(required_qty, item_doc.item_code))

	return locations

@frappe.whitelist()
def create_delivery_note(source_name, target_doc=None):
	pick_list = frappe.get_doc('Pick List', source_name)
	sales_orders = [d.sales_order for d in pick_list.locations]
	sales_orders = set(sales_orders)

	delivery_note = None
	for sales_order in sales_orders:
		delivery_note = create_delivery_note_from_sales_order(sales_order,
			delivery_note, skip_item_mapping=True)

	item_table_mapper = {
		'doctype': 'Delivery Note Item',
		'field_map': {
			'rate': 'rate',
			'name': 'so_detail',
			'parent': 'against_sales_order',
		},
		'condition': lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
	}

	for location in pick_list.locations:
		sales_order_item = frappe.get_cached_doc('Sales Order Item', location.sales_order_item)
		dn_item = map_child_doc(sales_order_item, delivery_note, item_table_mapper)

		if dn_item:
			dn_item.warehouse = location.warehouse
			dn_item.qty = location.picked_qty
			dn_item.batch_no = location.batch_no
			dn_item.serial_no = location.serial_no

			update_delivery_note_item(sales_order_item, dn_item, delivery_note)

	set_delivery_note_missing_values(delivery_note)

	delivery_note.pick_list = pick_list.name

	return delivery_note

@frappe.whitelist()
def create_stock_entry(pick_list):
	pick_list = frappe.get_doc(json.loads(pick_list))

	if stock_entry_exists(pick_list.get('name')):
		return frappe.msgprint(_('Stock Entry has been already created against this Pick List'))

	stock_entry = frappe.new_doc('Stock Entry')
	stock_entry.pick_list = pick_list.get('name')
	stock_entry.purpose = pick_list.get('purpose')
	stock_entry.set_stock_entry_type()

	if pick_list.get('work_order'):
		stock_entry = update_stock_entry_based_on_work_order(pick_list, stock_entry)
	elif pick_list.get('material_request'):
		stock_entry = update_stock_entry_based_on_material_request(pick_list, stock_entry)

	stock_entry.set_incoming_rate()
	stock_entry.set_actual_qty()
	stock_entry.calculate_rate_and_amount(update_finished_item_rate=False)

	return stock_entry.as_dict()

@frappe.whitelist()
def get_pending_work_orders(doctype, txt, searchfield, start, page_length, filters, as_dict):
	return frappe.db.sql("""
		SELECT
			`name`, `company`, `planned_start_date`
		FROM
			`tabWork Order`
		WHERE
			`status` not in ('Completed', 'Stopped')
			AND `qty` > `material_transferred_for_manufacturing`
			AND `docstatus` = 1
			AND `company` = %(company)s
			AND `name` like %(txt)s
		ORDER BY
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999), name
		LIMIT
			%(start)s, %(page_length)s""",
		{
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace('%', ''),
			'start': start,
			'page_length': frappe.utils.cint(page_length),
			'company': filters.get('company')
		}, as_dict=as_dict)

@frappe.whitelist()
def target_document_exists(pick_list_name, purpose):
	if purpose == 'Delivery against Sales Order':
		return frappe.db.exists('Delivery Note', {
			'pick_list': pick_list_name
		})

	return stock_entry_exists(pick_list_name)


def update_delivery_note_item(source, target, delivery_note):
	cost_center = frappe.db.get_value('Project', delivery_note.project, 'cost_center')
	if not cost_center:
		cost_center = get_cost_center(source.item_code, 'Item', delivery_note.company)

	if not cost_center:
		cost_center = get_cost_center(source.item_group, 'Item Group', delivery_note.company)

	target.cost_center = cost_center

def get_cost_center(for_item, from_doctype, company):
	'''Returns Cost Center for Item or Item Group'''
	return frappe.db.get_value('Item Default',
		fieldname=['buying_cost_center'],
		filters={
			'parent': for_item,
			'parenttype': from_doctype,
			'company': company
		})

def set_delivery_note_missing_values(target):
	target.run_method('set_missing_values')
	target.run_method('set_po_nos')
	target.run_method('calculate_taxes_and_totals')

def stock_entry_exists(pick_list_name):
	return frappe.db.exists('Stock Entry', {
		'pick_list': pick_list_name
	})

@frappe.whitelist()
def get_item_details(item_code, uom=None):
	details = frappe.db.get_value('Item', item_code, ['stock_uom', 'name'], as_dict=1)
	details.uom = uom or details.stock_uom
	if uom:
		details.update(get_conversion_factor(item_code, uom))

	return details


def update_stock_entry_based_on_work_order(pick_list, stock_entry):
	work_order = frappe.get_doc("Work Order", pick_list.get('work_order'))

	stock_entry.work_order = work_order.name
	stock_entry.company = work_order.company
	stock_entry.from_bom = 1
	stock_entry.bom_no = work_order.bom_no
	stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
	stock_entry.fg_completed_qty = pick_list.for_qty
	if work_order.bom_no:
		stock_entry.inspection_required = frappe.db.get_value('BOM',
			work_order.bom_no, 'inspection_required')

	is_wip_warehouse_group = frappe.db.get_value('Warehouse', work_order.wip_warehouse, 'is_group')
	if not (is_wip_warehouse_group and work_order.skip_transfer):
		wip_warehouse = work_order.wip_warehouse
	else:
		wip_warehouse = None
	stock_entry.to_warehouse = wip_warehouse

	stock_entry.project = work_order.project

	for location in pick_list.locations:
		item = frappe._dict()
		item.item_code = location.item_code
		item.s_warehouse = location.warehouse
		item.t_warehouse = wip_warehouse
		item.qty = location.picked_qty * location.conversion_factor
		item.transfer_qty = location.picked_qty
		item.uom = location.uom
		item.conversion_factor = location.conversion_factor
		item.stock_uom = location.stock_uom

		stock_entry.append('items', item)

	return stock_entry

def update_stock_entry_based_on_material_request(pick_list, stock_entry):
	for location in pick_list.locations:
		target_warehouse = None
		if location.material_request_item:
			target_warehouse = frappe.get_value('Material Request Item',
				location.material_request_item, 'warehouse')
		item = frappe._dict()
		item.item_code = location.item_code
		item.s_warehouse = location.warehouse
		item.t_warehouse = target_warehouse
		item.qty = location.picked_qty * location.conversion_factor
		item.transfer_qty = location.picked_qty
		item.uom = location.uom
		item.conversion_factor = location.conversion_factor
		item.stock_uom = location.stock_uom
		item.material_request = location.material_request
		item.material_request_item = location.material_request_item

		stock_entry.append('items', item)

	return stock_entry