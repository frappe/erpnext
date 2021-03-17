# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, cstr, cint
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from six import string_types

class Vehicle(Document):
	_copy_fields = [
		'company',
		'warehouse', 'sales_order',
		'customer', 'customer_name',
		'supplier', 'supplier_name',
		'purchase_document_type', 'purchase_document_no', 'purchase_date', 'purchase_time', 'purchase_rate',
		'delivery_document_type', 'delivery_document_no', 'delivery_date', 'delivery_time', 'sales_invoice',
		'warranty_expiry_date', 'amc_expiry_date'
	]

	def autoname(self):
		if self.flags.from_serial_no:
			self.name = self.flags.from_serial_no
		else:
			item = frappe.get_cached_doc("Item", self.item_code)
			serial_no_series = item.serial_no_series
			if serial_no_series:
				self.name = make_autoname(serial_no_series, "Serial No", item)

	def onload(self):
		self.copy_image_from_item()

	def on_update(self):
		self.update_vehicle_serial_no()
		self.update_vehicle_booking_order()

		self.db_set("last_odometer", get_vehicle_odometer(self.name))

	def validate(self):
		self.validate_item()
		self.validate_vehicle_id()

		self.update_reference_from_serial_no()

		self.copy_image_from_item()
		self.set_status()

	def on_trash(self):
		self.delete_serial_no_on_trash()

	def copy_image_from_item(self):
		if not self.image:
			self.image = frappe.get_cached_value('Item', self.item_code, 'image')

	def update_vehicle_serial_no(self):
		if self.flags.from_serial_no:
			serial_no_doc = frappe.get_cached_doc("Serial No", self.flags.from_serial_no)
			serial_no_doc.db_set('vehicle', self.name)
		else:
			if not frappe.db.exists("Serial No", self.name):
				serial_no_doc = frappe.new_doc("Serial No")
				serial_no_doc.flags.from_vehicle = self.name

				for fieldname in self._copy_fields:
					serial_no_doc.set(fieldname, self.get(fieldname))

				serial_no_doc.item_code = self.item_code
				serial_no_doc.serial_no = self.name
				serial_no_doc.vehicle = self.name
				serial_no_doc.insert(ignore_permissions=True)

				self.update_reference_from_serial_no(serial_no_doc)
				self.db_update()

	def update_vehicle_booking_order(self):
		orders = frappe.get_all("Vehicle Booking Order", filters={"docstatus": ['<', 2], "vehicle": self.name})
		for d in orders:
			doc = frappe.get_doc("Vehicle Booking Order", d.name)
			doc.set_vehicle_details(update=True)
			doc.notify_update()

	def validate_item(self):
		item = frappe.get_cached_doc("Item", self.item_code)
		if not item.is_vehicle:
			frappe.throw(_("Item {0} is not setup as a Vehicle Item").format(self.item_code))

		self.item_group = item.item_group
		self.item_name = item.item_name
		self.brand = item.brand
		self.warranty_period = item.warranty_period

	def validate_vehicle_id(self):
		import re

		if self.unregistered:
			self.license_plate = ""

		self.chassis_no = re.sub(r"\s+", "", cstr(self.chassis_no).upper())
		self.engine_no = re.sub(r"\s+", "", cstr(self.engine_no).upper())
		self.license_plate = re.sub(r"\s+", "", cstr(self.license_plate).upper())

		exclude = None if self.is_new() else self.name
		validate_duplicate_vehicle('chassis_no', self.chassis_no, exclude=exclude, throw=True)
		validate_duplicate_vehicle('engine_no', self.engine_no, exclude=exclude, throw=True)
		validate_duplicate_vehicle('license_plate', self.license_plate, exclude=exclude, throw=True)

	def update_reference_from_serial_no(self, serial_no_doc=None):
		if not serial_no_doc:
			serial_no_doc = self.get_serial_no_doc()

		if not serial_no_doc:
			return

		if cstr(self.get('sales_order')) != cstr(self.db_get('sales_order')):
			serial_no_doc.sales_order = self.sales_order
			serial_no_doc.flags.from_vehicle = self.name
			serial_no_doc.save()

		for f in self._copy_fields:
			self.set(f, serial_no_doc.get(f))

	def delete_serial_no_on_trash(self):
		if frappe.db.exists("Serial No", self.name):
			frappe.delete_doc("Serial No", self.name)

	def get_serial_no_doc(self):
		serial_no_doc = None
		if self.flags.from_serial_no:
			serial_no_doc = frappe.get_cached_doc("Serial No", self.flags.from_serial_no)
		else:
			serial_no_name = frappe.db.get_value("Serial No", {"vehicle": self.name}, "name")
			if serial_no_name:
				serial_no_doc = frappe.get_doc("Serial No", serial_no_name)

		return serial_no_doc

	def set_status(self):
		if self.delivery_document_type:
			self.status = "Delivered"
		elif self.warranty_expiry_date and getdate(self.warranty_expiry_date) <= getdate(nowdate()):
			self.status = "Expired"
		elif not self.warehouse:
			self.status = "Inactive"
		else:
			self.status = "Active"


def split_vehicle_items_by_qty(doc):
	new_rows = []
	for d in doc.items:
		new_rows.append(d)
		if d.qty > 1 and d.item_code and frappe.get_cached_value("Item", d.item_code, "is_vehicle"):
			qty = cint(d.qty)
			d.qty = 1

			for i in range(qty - 1):
				new_rows.append(frappe.copy_doc(d))

	doc.items = new_rows
	for i, d in enumerate(doc.items):
		d.idx = i + 1


def get_reserved_vehicles(sales_order, additional_filters=None):
	if isinstance(sales_order, list):
		sales_order_cond = ['in', sales_order]
	else:
		sales_order_cond = sales_order

	filters = {
		'sales_order': sales_order_cond,
	}
	if additional_filters:
		filters.update(additional_filters)

	return frappe.get_all("Vehicle",
		fields=[
			'name', 'item_code', 'warehouse', 'sales_order',
			'delivery_document_type', 'delivery_document_no',
			'purchase_document_type', 'purchase_document_no',
		],
		filters=filters,
		order_by="timestamp(purchase_date, purchase_time) desc")  # desc because popping from list


def set_reserved_vehicles_from_so(source, target):
	additional_filters = None
	if target.doctype == "Delivery Note" or (target.doctype == "Sales Invoice" and target.update_stock):
		additional_filters = {
			'delivery_document_no': ['is', 'not set'],
		}

	def get_key(row):
		return cstr(row.item_code), cstr(row.warehouse)

	vehicles = get_reserved_vehicles(source.name, additional_filters)
	if not vehicles:
		return

	vehicle_map = {}
	for d in vehicles:
		key = get_key(d)
		vehicle_map.setdefault(key, []).append(d.name)

	# set vehicles with warehouse first
	for d in target.items:
		key = get_key(d)
		if key in vehicle_map:
			item_vehicle_list = vehicle_map.get(key)
			if item_vehicle_list:
				d.vehicle = item_vehicle_list.pop()

	# set vehicles without warehouse too
	for d in target.items:
		if d.vehicle:
			continue

		key = (d.item_code, "")
		if key in vehicle_map:
			item_vehicle_list = vehicle_map.get(key)
			if item_vehicle_list:
				d.vehicle = item_vehicle_list.pop()


def set_reserved_vehicles_from_po(source, target):
	sales_orders = [d.get('sales_order') for d in source.items if d.get('sales_order')]
	additional_filters = None
	if target.doctype == "Purchase Receipt" or (target.doctype == "Purchase Invoice" and target.update_stock):
		additional_filters = {
			'purchase_document_no': ['is', 'not set'],
			'warehouse': ['is', 'not set'],
		}

	vehicles = get_reserved_vehicles(sales_orders, additional_filters)
	vehicle_map = {}
	for d in vehicles:
		key = (d.item_code, d.sales_order)
		vehicle_map.setdefault(key, []).append(d.name)

	for d in target.items:
		row_sales_order = source.getone('items', filters={'name': d.get('purchase_order_item') or d.get('po_detail')})
		row_sales_order = row_sales_order.sales_order if row_sales_order else ""
		key = (d.item_code, row_sales_order)
		if key in vehicle_map:
			item_vehicle_list = vehicle_map.get(key)
			if item_vehicle_list:
				d.vehicle = item_vehicle_list.pop()


@frappe.whitelist()
def get_sales_order_vehicle_qty(sales_order):
	vehicle_item_rows = frappe.db.sql("""
		select item_code, sum(qty)
		from `tabSales Order Item`
		where docstatus = 1 and parent = %s and is_vehicle = 1
		group by item_code
	""", sales_order)

	ordered_qty_map = dict(vehicle_item_rows) if vehicle_item_rows else {}
	vehicle_item_codes = list(ordered_qty_map.keys())

	if not vehicle_item_rows:
		frappe.throw(_("No Vehicle Items found in {0}").format(sales_order))

	actual_qty_map = frappe.db.sql("""
		select item_code, sum(actual_qty)
		from `tabBin`
		where item_code in %s
		group by item_code
	""", [vehicle_item_codes])
	actual_qty_map = dict(actual_qty_map) if actual_qty_map else {}

	reserved_qty_map = get_reserved_vehicle_qty(sales_order)

	result = {}
	empty_dict = {"actual_qty": 0, "reserved_qty": 0, "ordered_qty": 0}

	for item_code, reserved_qty in reserved_qty_map.items():
		result.setdefault(item_code, empty_dict.copy())
		result[item_code]['reserved_qty'] += reserved_qty

	for item_code, actual_qty in actual_qty_map.items():
		result.setdefault(item_code, empty_dict.copy())
		result[item_code]['actual_qty'] += actual_qty

	for item_code, ordered_qty in ordered_qty_map.items():
		result.setdefault(item_code, empty_dict.copy())
		result[item_code]['ordered_qty'] += ordered_qty

	out = []
	for item_code, qty_dict in result.items():
		qty_dict['item_code'] = item_code
		qty_dict['to_create_qty'] = qty_dict['ordered_qty'] - qty_dict['reserved_qty']
		out.append(qty_dict)

	return out


def get_reserved_vehicle_qty(sales_order):
	reserved_qty_map = frappe.db.sql("""
		select item_code, count(name)
		from `tabVehicle`
		where sales_order = %s
		group by item_code
	""", sales_order)

	reserved_qty_map = dict(reserved_qty_map) if reserved_qty_map else {}
	return reserved_qty_map


@frappe.whitelist()
def create_vehicle_from_so(sales_order, to_reserve_qty_map=None):
	if not to_reserve_qty_map:
		to_reserve_qty_map = {}
	elif isinstance(to_reserve_qty_map, string_types):
		to_reserve_qty_map = frappe.parse_json(to_reserve_qty_map)

	so_doc = frappe.get_doc("Sales Order", sales_order)
	if so_doc.docstatus != 1:
		frappe.throw(_("Sales Order must be submitted to create reserved Vehicles"))

	ordered_qty_map = {}
	update_to_reserve_qty = not to_reserve_qty_map
	for d in so_doc.items:
		if d.is_vehicle:
			ordered_qty_map.setdefault(d.item_code, 0)
			ordered_qty_map[d.item_code] += d.qty

			if update_to_reserve_qty:
				to_reserve_qty_map.setdefault(d.item_code, 0)
				to_reserve_qty_map[d.item_code] += d.qty

	reserved_qty_map = get_reserved_vehicle_qty(sales_order)
	vehicle_item_codes = list(set([d.item_code for d in so_doc.items if d.item_code and d.is_vehicle and d.qty]))
	vehicles_created = []

	for item_code, to_reserve_qty in to_reserve_qty_map.items():
		if item_code not in vehicle_item_codes:
			frappe.throw(_("Cannot create reserved {0} Vehicle because it does not exist in this Sales Order")
				.format(frappe.bold(item_code)))

		to_reserve_qty = cint(to_reserve_qty)
		existing_qty = cint(reserved_qty_map.get(item_code, 0))
		ordered_qty = cint(ordered_qty_map.get(item_code, 0))

		if to_reserve_qty + existing_qty > ordered_qty:
			frappe.throw(_("Cannot create {0} reserved {1} Vehicles because it would exceed Ordered Qty {2}")
				.format(frappe.bold(to_reserve_qty), frappe.bold(item_code), frappe.bold(ordered_qty)))

		for i in range(to_reserve_qty):
			vehicle_doc = frappe.new_doc("Vehicle")
			vehicle_doc.item_code = item_code
			vehicle_doc.sales_order = sales_order
			vehicle_doc.save()

			vehicles_created.append(vehicle_doc)

	if not vehicles_created:
		frappe.msgprint(_("Nothing to create").format(sales_order))
	else:
		links = [frappe.utils.get_link_to_form('Vehicle', d.name) for d in vehicles_created]
		frappe.msgprint(_("Reserved Vehicles created: {0}").format(", ".join(links)))


@frappe.whitelist()
def validate_duplicate_vehicle(fieldname, value, exclude=None, throw=False):
	if not value:
		return

	meta = frappe.get_meta("Vehicle")
	if not fieldname or not meta.has_field(fieldname):
		frappe.throw(_("Invalid fieldname {0}").format(fieldname))

	label = _(meta.get_field(fieldname).label)

	filters = {fieldname: value}
	if exclude:
		filters['name'] = ['!=', exclude]

	duplicates = frappe.db.get_all("Vehicle", filters=filters)
	duplicate_names = [d.name for d in duplicates]
	if duplicates:
		frappe.msgprint(_("{0} {1} is already set in Vehicle: {2}").format(label, frappe.bold(value),
			", ".join([frappe.utils.get_link_to_form("Vehicle", name) for name in duplicate_names])),
			raise_exception=throw, indicator='red' if throw else 'orange')


@frappe.whitelist()
def get_vehicle_odometer(vehicle, date=None, project=None, ascending=False):
	if not vehicle:
		frappe.throw(_("Vehicle not provided"))

	filters = {
		"vehicle": vehicle,
		"docstatus": 1,
		"date": ['<=', date]
	}

	if project:
		filters['project'] = project
	if date:
		filters['date'] = ['<=', getdate(date)]

	asc_or_desc = "asc" if ascending else "desc"
	order_by = "date {0}, creation {0}".format(asc_or_desc)

	odometer = frappe.get_all("Vehicle Log", filters=filters, fields=['odometer'], order_by=order_by, limit_page_length=1)

	return cint(odometer[0].odometer) if odometer else 0


def get_project_odometer(project, vehicle):
	first_odometer = get_vehicle_odometer(vehicle, project=project, ascending=True)
	last_odometer = get_vehicle_odometer(vehicle, project=project, ascending=False)
	return first_odometer, last_odometer
