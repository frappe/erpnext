# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from six import iteritems
from frappe.model.document import Document
from frappe import _
from collections import OrderedDict
from frappe.utils import floor, flt, today, cint
from frappe.model.mapper import get_mapped_doc, map_child_doc
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as create_delivery_note_from_sales_order

# TODO: Prioritize SO or WO group warehouse

class PickList(Document):
	def before_save(self):
		self.set_item_locations()

	def before_submit(self):
		for item in self.locations:
			if not frappe.get_cached_value('Item', item.item_code, 'has_serial_no'):
				continue
			if not item.serial_no:
				frappe.throw(_("Row #{0}: {1} does not have any available serial numbers in {2}".format(
					frappe.bold(item.idx), frappe.bold(item.item_code), frappe.bold(item.warehouse))),
					title=_("Serial Nos Required"))
			if len(item.serial_no.split('\n')) == item.picked_qty:
				continue
			frappe.throw(_('For item {0} at row {1}, count of serial numbers does not match with the picked quantity')
				.format(frappe.bold(item.item_code), frappe.bold(item.idx)), title=_("Quantity Mismatch"))

	def set_item_locations(self, save=False):
		items = self.aggregate_item_qty()
		self.item_location_map = frappe._dict()

		from_warehouses = None
		if self.parent_warehouse:
			from_warehouses = frappe.db.get_descendants('Warehouse', self.parent_warehouse)

		# Create replica before resetting, to handle empty table on update after submit.
		locations_replica  = self.get('locations')

		# reset
		self.delete_key('locations')
		for item_doc in items:
			item_code = item_doc.item_code

			self.item_location_map.setdefault(item_code,
				get_available_item_locations(item_code, from_warehouses, self.item_count_map.get(item_code), self.company))

			locations = get_items_with_location_and_quantity(item_doc, self.item_location_map, self.docstatus)

			item_doc.idx = None
			item_doc.name = None

			for row in locations:
				row.update({
					'picked_qty': row.stock_qty
				})

				location = item_doc.as_dict()
				location.update(row)
				self.append('locations', location)

		# If table is empty on update after submit, set stock_qty, picked_qty to 0 so that indicator is red
		# and give feedback to the user. This is to avoid empty Pick Lists.
		if not self.get('locations') and self.docstatus == 1:
			for location in locations_replica:
				location.stock_qty = 0
				location.picked_qty = 0
				self.append('locations', location)
			frappe.msgprint(_("Please Restock Items and Update the Pick List to continue. To discontinue, cancel the Pick List."),
				 title=_("Out of Stock"), indicator="red")

		if save:
			self.save()

	def aggregate_item_qty(self):
		locations = self.get('locations')
		self.item_count_map = {}
		# aggregate qty for same item
		item_map = OrderedDict()
		for item in locations:
			if not item.item_code:
				frappe.throw("Row #{0}: Item Code is Mandatory".format(item.idx))
			item_code = item.item_code
			reference = item.sales_order_item or item.material_request_item
			key = (item_code, item.uom, reference)

			item.idx = None
			item.name = None

			if item_map.get(key):
				item_map[key].qty += item.qty
				item_map[key].stock_qty += item.stock_qty
			else:
				item_map[key] = item

			# maintain count of each item (useful to limit get query)
			self.item_count_map.setdefault(item_code, 0)
			self.item_count_map[item_code] += item.stock_qty

		return item_map.values()


def validate_item_locations(pick_list):
	if not pick_list.locations:
		frappe.throw(_("Add items in the Item Locations table"))

def get_items_with_location_and_quantity(item_doc, item_location_map, docstatus):
	available_locations = item_location_map.get(item_doc.item_code)
	locations = []

	# if stock qty is zero on submitted entry, show positive remaining qty to recalculate in case of restock.
	remaining_stock_qty = item_doc.qty if (docstatus == 1 and item_doc.stock_qty == 0) else item_doc.stock_qty

	while remaining_stock_qty > 0 and available_locations:
		item_location = available_locations.pop(0)
		item_location = frappe._dict(item_location)

		stock_qty = remaining_stock_qty if item_location.qty >= remaining_stock_qty else item_location.qty
		qty = stock_qty / (item_doc.conversion_factor or 1)

		uom_must_be_whole_number = frappe.db.get_value('UOM', item_doc.uom, 'must_be_whole_number')
		if uom_must_be_whole_number:
			qty = floor(qty)
			stock_qty = qty * item_doc.conversion_factor
			if not stock_qty: break

		serial_nos = None
		if item_location.serial_no:
			serial_nos = '\n'.join(item_location.serial_no[0: cint(stock_qty)])

		locations.append(frappe._dict({
			'qty': qty,
			'stock_qty': stock_qty,
			'warehouse': item_location.warehouse,
			'serial_no': serial_nos,
			'batch_no': item_location.batch_no
		}))

		remaining_stock_qty -= stock_qty

		qty_diff = item_location.qty - stock_qty
		# if extra quantity is available push current warehouse to available locations
		if qty_diff > 0:
			item_location.qty = qty_diff
			if item_location.serial_no:
				# set remaining serial numbers
				item_location.serial_no = item_location.serial_no[-int(qty_diff):]
			available_locations = [item_location] + available_locations

	# update available locations for the item
	item_location_map[item_doc.item_code] = available_locations
	return locations

def get_available_item_locations(item_code, from_warehouses, required_qty, company, ignore_validation=False):
	locations = []
	has_serial_no  = frappe.get_cached_value('Item', item_code, 'has_serial_no')
	has_batch_no = frappe.get_cached_value('Item', item_code, 'has_batch_no')

	if has_batch_no and has_serial_no:
		locations = get_available_item_locations_for_serial_and_batched_item(item_code, from_warehouses, required_qty, company)
	elif has_serial_no:
		locations = get_available_item_locations_for_serialized_item(item_code, from_warehouses, required_qty, company)
	elif has_batch_no:
		locations = get_available_item_locations_for_batched_item(item_code, from_warehouses, required_qty, company)
	else:
		locations = get_available_item_locations_for_other_item(item_code, from_warehouses, required_qty, company)

	total_qty_available = sum(location.get('qty') for location in locations)

	remaining_qty = required_qty - total_qty_available

	if remaining_qty > 0 and not ignore_validation:
		frappe.msgprint(_('{0} units of Item {1} is not available.')
			.format(remaining_qty, frappe.get_desk_link('Item', item_code)),
			title=_("Insufficient Stock"))

	return locations


def get_available_item_locations_for_serialized_item(item_code, from_warehouses, required_qty, company):
	filters = frappe._dict({
		'item_code': item_code,
		'company': company,
		'warehouse': ['!=', '']
	})

	if from_warehouses:
		filters.warehouse = ['in', from_warehouses]

	serial_nos = frappe.get_all('Serial No',
		fields=['name', 'warehouse'],
		filters=filters,
		limit=required_qty,
		order_by='purchase_date',
		as_list=1)

	warehouse_serial_nos_map = frappe._dict()
	for serial_no, warehouse in serial_nos:
		warehouse_serial_nos_map.setdefault(warehouse, []).append(serial_no)

	locations = []
	for warehouse, serial_nos in iteritems(warehouse_serial_nos_map):
		locations.append({
			'qty': len(serial_nos),
			'warehouse': warehouse,
			'serial_no': serial_nos
		})

	return locations

def get_available_item_locations_for_batched_item(item_code, from_warehouses, required_qty, company):
	warehouse_condition = 'and warehouse in %(warehouses)s' if from_warehouses else ''
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
			and sle.`company` = %(company)s
			and batch.disabled = 0
			and IFNULL(batch.`expiry_date`, '2200-01-01') > %(today)s
			{warehouse_condition}
		GROUP BY
			`warehouse`,
			`batch_no`,
			`item_code`
		HAVING `qty` > 0
		ORDER BY IFNULL(batch.`expiry_date`, '2200-01-01'), batch.`creation`
	""".format(warehouse_condition=warehouse_condition), { #nosec
		'item_code': item_code,
		'company': company,
		'today': today(),
		'warehouses': from_warehouses
	}, as_dict=1)

	return batch_locations

def get_available_item_locations_for_serial_and_batched_item(item_code, from_warehouses, required_qty, company):
	# Get batch nos by FIFO
	locations = get_available_item_locations_for_batched_item(item_code, from_warehouses, required_qty, company)

	filters = frappe._dict({
		'item_code': item_code,
		'company': company,
		'warehouse': ['!=', ''],
		'batch_no': ''
	})

	# Get Serial Nos by FIFO for Batch No
	for location in locations:
		filters.batch_no = location.batch_no
		filters.warehouse = location.warehouse
		location.qty = required_qty if location.qty > required_qty else location.qty # if extra qty in batch

		serial_nos = frappe.get_list('Serial No',
			fields=['name'],
			filters=filters,
			limit=location.qty,
			order_by='purchase_date')

		serial_nos = [sn.name for sn in serial_nos]
		location.serial_no = serial_nos

	return locations

def get_available_item_locations_for_other_item(item_code, from_warehouses, required_qty, company):
	# gets all items available in different warehouses
	warehouses = [x.get('name') for x in frappe.get_list("Warehouse", {'company': company}, "name")]

	filters = frappe._dict({
		'item_code': item_code,
		'warehouse': ['in', warehouses],
		'actual_qty': ['>', 0]
	})

	if from_warehouses:
		filters.warehouse = ['in', from_warehouses]

	item_locations = frappe.get_all('Bin',
		fields=['warehouse', 'actual_qty as qty'],
		filters=filters,
		limit=required_qty,
		order_by='creation')

	return item_locations


@frappe.whitelist()
def create_delivery_note(source_name, target_doc=None):
	pick_list = frappe.get_doc('Pick List', source_name)
	validate_item_locations(pick_list)

	sales_orders = [d.sales_order for d in pick_list.locations if d.sales_order]
	sales_orders = set(sales_orders)

	delivery_note = None
	for sales_order in sales_orders:
		delivery_note = create_delivery_note_from_sales_order(sales_order,
			delivery_note, skip_item_mapping=True)

	# map rows without sales orders as well
	if not delivery_note:
		delivery_note = frappe.new_doc("Delivery Note")

	item_table_mapper = {
		'doctype': 'Delivery Note Item',
		'field_map': {
			'rate': 'rate',
			'name': 'so_detail',
			'parent': 'against_sales_order',
		},
		'condition': lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
	}

	item_table_mapper_without_so = {
		'doctype': 'Delivery Note Item',
		'field_map': {
			'rate': 'rate',
			'name': 'name',
			'parent': '',
		}
	}

	for location in pick_list.locations:
		if location.sales_order_item:
			sales_order_item = frappe.get_cached_doc('Sales Order Item', {'name':location.sales_order_item})
		else:
			sales_order_item = None

		source_doc, table_mapper = [sales_order_item, item_table_mapper] if sales_order_item \
			else [location, item_table_mapper_without_so]

		dn_item = map_child_doc(source_doc, delivery_note, table_mapper)

		if dn_item:
			dn_item.warehouse = location.warehouse
			dn_item.qty = location.picked_qty
			dn_item.batch_no = location.batch_no
			dn_item.serial_no = location.serial_no

			update_delivery_note_item(source_doc, dn_item, delivery_note)

	set_delivery_note_missing_values(delivery_note)

	delivery_note.pick_list = pick_list.name
	delivery_note.customer = pick_list.customer if pick_list.customer else None

	return delivery_note

@frappe.whitelist()
def create_stock_entry(pick_list):
	pick_list = frappe.get_doc(json.loads(pick_list))
	validate_item_locations(pick_list)

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
	else:
		stock_entry = update_stock_entry_items_with_no_reference(pick_list, stock_entry)

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
	if purpose == 'Delivery':
		return frappe.db.exists('Delivery Note', {
			'pick_list': pick_list_name
		})

	return stock_entry_exists(pick_list_name)

@frappe.whitelist()
def get_item_details(item_code, uom=None):
	details = frappe.db.get_value('Item', item_code, ['stock_uom', 'name'], as_dict=1)
	details.uom = uom or details.stock_uom
	if uom:
		details.update(get_conversion_factor(item_code, uom))

	return details


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
		update_common_item_properties(item, location)
		item.t_warehouse = wip_warehouse

		stock_entry.append('items', item)

	return stock_entry

def update_stock_entry_based_on_material_request(pick_list, stock_entry):
	for location in pick_list.locations:
		target_warehouse = None
		if location.material_request_item:
			target_warehouse = frappe.get_value('Material Request Item',
				location.material_request_item, 'warehouse')
		item = frappe._dict()
		update_common_item_properties(item, location)
		item.t_warehouse = target_warehouse
		stock_entry.append('items', item)

	return stock_entry

def update_stock_entry_items_with_no_reference(pick_list, stock_entry):
	for location in pick_list.locations:
		item = frappe._dict()
		update_common_item_properties(item, location)

		stock_entry.append('items', item)

	return stock_entry

def update_common_item_properties(item, location):
	item.item_code = location.item_code
	item.s_warehouse = location.warehouse
	item.qty = location.picked_qty * location.conversion_factor
	item.transfer_qty = location.picked_qty
	item.uom = location.uom
	item.conversion_factor = location.conversion_factor
	item.stock_uom = location.stock_uom
	item.material_request = location.material_request
	item.serial_no = location.serial_no
	item.batch_no = location.batch_no
	item.material_request_item = location.material_request_item
