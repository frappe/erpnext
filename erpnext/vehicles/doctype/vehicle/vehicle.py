# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.vehicles.doctype.vehicle_log.vehicle_log import get_vehicle_odometer, get_customer_vehicle_selector_data
from frappe import _
from frappe.utils import getdate, nowdate, cstr, cint
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from erpnext.vehicles.utils import format_vehicle_id
from six import string_types


class Vehicle(Document):
	_copy_fields = [
		'company',
		'warehouse', 'sales_order',
		'customer', 'customer_name', 'vehicle_owner', 'vehicle_owner_name',
		'is_reserved', 'reserved_customer', 'reserved_customer_name',
		'supplier', 'supplier_name',
		'purchase_document_type', 'purchase_document_no', 'purchase_date', 'purchase_time', 'purchase_rate',
		'delivery_document_type', 'delivery_document_no', 'delivery_date', 'delivery_time', 'sales_invoice',
		'warranty_expiry_date', 'amc_expiry_date', 'maintenance_status'
	]

	_sync_fields = [
		'item_code', 'sales_order', 'is_reserved', 'reserved_customer', 'reserved_customer_name', 'delivery_date',
	]

	def __init__(self, *args, **kwargs):
		super(Vehicle, self).__init__(*args, **kwargs)
		self.via_stock_ledger = False

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
		self.set_onload('stock_exists', self.stock_ledger_created())
		self.set_onload('cant_change_fields', self.get_cant_change_fields())

		if not self.is_new():
			self.set_onload('customer_vehicle_selector_data', get_customer_vehicle_selector_data(vehicle=self.name))

	def validate(self):
		self.validate_item()
		self.validate_vehicle_id()
		self.copy_image_from_item()

		self.sync_with_serial_no()

		self.set_invoice_status()
		self.set_status()

		self.validate_cant_change()

	def on_update(self):
		self.create_vehicle_serial_no()

		if not self.via_stock_ledger and not self.flags.from_serial_no:
			self.update_vehicle_booking_order()

		self.db_set("last_odometer", get_vehicle_odometer(self.name))

	def on_trash(self):
		self.delete_serial_no_on_trash()

	def delete_serial_no_on_trash(self):
		if frappe.db.exists("Serial No", self.name):
			frappe.delete_doc("Serial No", self.name, ignore_permissions=True)

	def copy_image_from_item(self):
		if not self.image:
			self.image = frappe.get_cached_value('Item', self.item_code, 'image')

	def validate_item(self):
		item = frappe.get_cached_doc("Item", self.item_code)
		if not item.is_vehicle:
			frappe.throw(_("Item {0} is not setup as a Vehicle Item").format(self.item_code))

		self.item_group = item.item_group
		self.item_name = item.item_name
		self.brand = item.brand
		self.warranty_period = item.warranty_period

		self.variant_of = item.variant_of
		self.variant_of_name = frappe.get_cached_value("Item", self.variant_of, 'item_name') if self.variant_of else None

	def validate_vehicle_id(self):
		if self.unregistered:
			self.license_plate = ""

		self.chassis_no = format_vehicle_id(self.chassis_no)
		self.engine_no = format_vehicle_id(self.engine_no)
		self.license_plate = format_vehicle_id(self.license_plate)

		exclude = None if self.is_new() else self.name
		validate_duplicate_vehicle('chassis_no', self.chassis_no, exclude=exclude, throw=True)
		validate_duplicate_vehicle('engine_no', self.engine_no, exclude=exclude, throw=True)
		validate_duplicate_vehicle('license_plate', self.license_plate, exclude=exclude, throw=True)

	def sync_with_serial_no(self, serial_no_doc=None):
		if not serial_no_doc:
			serial_no_doc = self.get_serial_no_doc()

		if not serial_no_doc:
			return

		serial_no_doc.flags.allow_change_item_code = True

		before_values_sync = frappe.db.get_value(self.doctype, self.name, self._sync_fields, as_dict=1)
		to_sync = any([before_values_sync.get(key) != self.get(key) for key in before_values_sync])

		if to_sync:
			for key in self._sync_fields:
				serial_no_doc.set(key, self.get(key))

			serial_no_doc.flags.from_vehicle = self.name
			serial_no_doc.save(ignore_permissions=1)

		for f in self._copy_fields:
			self.set(f, serial_no_doc.get(f))

	def get_serial_no_doc(self):
		serial_no_doc = None
		if self.flags.from_serial_no:
			serial_no_doc = frappe.get_cached_doc("Serial No", self.flags.from_serial_no)
		else:
			serial_no_name = frappe.db.get_value("Serial No", {"vehicle": self.name}, "name")
			if serial_no_name:
				serial_no_doc = frappe.get_doc("Serial No", serial_no_name)

		return serial_no_doc

	def create_vehicle_serial_no(self):
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

				self.sync_with_serial_no(serial_no_doc)
				self.db_update()

	def update_vehicle_booking_order(self):
		orders = frappe.get_all("Vehicle Booking Order", filters={
			"docstatus": 1,
			"vehicle": self.name,
			"delivery_status": 'Not Received',
			"invoice_status": 'Not Received'
		})
		for d in orders:
			doc = frappe.get_doc("Vehicle Booking Order", d.name)
			doc.set_vehicle_details(update=True)
			doc.notify_update()

	def set_invoice_status(self, update=False, update_modified=True):
		vehicle_invoice = frappe.db.get_value("Vehicle Invoice", filters={'vehicle': self.name, 'docstatus': 1},
			fieldname=['status', 'issued_for'], as_dict=1)

		if vehicle_invoice:
			self.invoice_status = vehicle_invoice.status
			self.invoice_issued_for = vehicle_invoice.issued_for if self.invoice_status == "Issued" else None
		else:
			self.invoice_status = 'Not Received'
			self.invoice_issued_for = None

		if update:
			self.db_set({
				'invoice_status': self.invoice_status,
				'invoice_issued_for': self.invoice_issued_for
			}, update_modified=update_modified)

	def set_status(self):
		if self.delivery_document_type:
			self.status = "Delivered"
		elif self.warranty_expiry_date and getdate(self.warranty_expiry_date) <= getdate(nowdate()):
			self.status = "Expired"
		elif not self.warehouse:
			self.status = "Inactive"
		else:
			self.status = "Active"

	def validate_cant_change(self):
		if self.is_new():
			return

		fields = self.get_cant_change_fields()
		cant_change_fields = [f for f, cant_change in fields.items() if cant_change]

		if cant_change_fields:
			previous_values = frappe.db.get_value(self.doctype, self.name, cant_change_fields, as_dict=1)
			for f, old_value in previous_values.items():
				if cstr(self.get(f)) != cstr(old_value):
					label = self.meta.get_label(f)
					frappe.throw(_("Cannot change {0} because transactions already exists for this Vehicle")
						.format(frappe.bold(label)))

	def get_cant_change_fields(self):
		ledger_or_invoice_exists = self.stock_ledger_created() or self.vehicle_invoice_created()
		order_exists = self.vehicle_booking_order_created() or self.vehicle_registration_order_created()
		return frappe._dict({
			'item_code': ledger_or_invoice_exists or order_exists,
			'chassis_no': ledger_or_invoice_exists,
		})

	def stock_ledger_created(self):
		if not hasattr(self, '_stock_ledger_created'):
			self._stock_ledger_created = len(frappe.db.sql("""
				select name
				from `tabStock Ledger Entry`
				where exists(select sr.name from `tabStock Ledger Entry Serial No` sr
					where sr.parent = `tabStock Ledger Entry`.name and sr.serial_no = %s)
				limit 1
			""", self.name))
		return self._stock_ledger_created

	def vehicle_invoice_created(self):
		if not hasattr(self, '_vehicle_invoice_created'):
			self._vehicle_invoice_created = frappe.db.exists("Vehicle Invoice", {'vehicle': self.name, 'docstatus': 1})
		return self._vehicle_invoice_created

	def vehicle_booking_order_created(self):
		if not hasattr(self, '_vehicle_booking_order_created'):
			self._vehicle_booking_order_created = frappe.db.exists("Vehicle Booking Order", {'vehicle': self.name, 'docstatus': 1})
		return self._vehicle_booking_order_created

	def vehicle_registration_order_created(self):
		if not hasattr(self, '_vehicle_registration_order_created'):
			self._vehicle_registration_order_created = frappe.db.exists("Vehicle Registration Order", {'vehicle': self.name, 'docstatus': 1})
		return self._vehicle_registration_order_created


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
		row_sales_order = source.getone('items', filters={'name': d.get('purchase_order_item') or d.get('purchase_order_item')})
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
def warn_vehicle_reserved(vehicle, customer=None):
	vehicle_details = frappe.db.get_value("Vehicle", vehicle,
		['is_reserved', 'reserved_customer', 'reserved_customer_name'], as_dict=1)

	if not vehicle_details:
		return

	if cint(vehicle_details.is_reserved):
		if vehicle_details.reserved_customer:
			if vehicle_details.reserved_customer != customer:
				frappe.msgprint(_("{0} is reserved for Customer {1}").format(
					frappe.get_desk_link("Vehicle", vehicle),
					frappe.bold(vehicle_details.reserved_customer_name or vehicle_details.reserved_customer)),
				title="Reserved", indicator="orange")
		else:
			frappe.msgprint(_("{0} is reserved without a Customer").format(frappe.get_desk_link("Vehicle", vehicle)),
				title="Reserved", indicator="orange")


@frappe.whitelist()
def get_vehicle_image(vehicle=None, item_code=None):
	image = None

	if vehicle:
		vehicle_details = frappe.db.get_value("Vehicle", vehicle, ['item_code', 'image'], as_dict=1)
		if vehicle_details:
			item_code = vehicle_details.item_code
			image = vehicle_details.image

	if not image and item_code:
		image = frappe.get_cached_value("Item", item_code, 'image')

	return image
