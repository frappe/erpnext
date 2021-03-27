# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub, unscrub
from frappe.utils import flt, cstr, getdate
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
from frappe.desk.query_report import group_report_data


class VehicleStockReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.to_date = getdate(self.filters.to_date)

		if getdate(self.filters.from_date) > self.filters.to_date:
			frappe.throw(_("From Date cannot be after To Date"))

	def run(self):
		self.get_item_data()
		self.get_stock_ledger_entries()
		self.process_sle()
		self.get_dispatched_vehicles()
		self.get_vehicle_data()
		self.get_vehicle_receipt_delivery_data()
		self.get_booking_data()
		self.prepare_data()

		columns = self.get_columns()

		data = self.get_grouped_data()

		return columns, data

	def get_stock_ledger_entries(self):
		self.sle = []

		self.filters.item_codes = list(self.item_data.keys())
		if not self.filters.item_codes:
			return self.sle

		sle_conditions = self.get_sle_conditions()
		self.sle = frappe.db.sql("""
			select posting_date, serial_no, voucher_type, voucher_no,
				item_code, warehouse, actual_qty, project, party_type, party
			from `tabStock Ledger Entry`
			where posting_date <= %(to_date)s {0}
			order by posting_date asc, posting_time asc, creation asc
		""".format(sle_conditions), self.filters, as_dict=1)

		return self.sle

	def process_sle(self):
		vehicles_in_stock = {}
		vehicles_delivered = []

		empty_vehicle_dict = frappe._dict({
			"qty": 0,
		})

		for sle in self.sle:
			key = (sle.item_code, sle.serial_no)

			# Item Code, Warehouse and Vehicle
			vehicle_dict = vehicles_in_stock.setdefault(key, empty_vehicle_dict.copy())
			vehicle_dict.item_code = sle.item_code
			vehicle_dict.vehicle = sle.serial_no
			vehicle_dict.warehouse = sle.warehouse

			# In Stock or not
			vehicle_dict.qty = flt(vehicle_dict.qty + sle.actual_qty, 0)

			# Receiving and Delivery
			if sle.actual_qty > 0:
				vehicle_dict.received_date = sle.posting_date
				vehicle_dict.received_dt = sle.voucher_type
				vehicle_dict.received_dn = sle.voucher_no

				vehicle_dict.delivery_date = None
				vehicle_dict.delivery_dt = None
				vehicle_dict.delivery_dn = None
			else:
				vehicle_dict.delivery_date = sle.posting_date
				vehicle_dict.delivery_dt = sle.voucher_type
				vehicle_dict.delivery_dn = sle.voucher_no

			# Project
			if sle.actual_qty > 0 or (sle.actual_qty < 0 and not vehicle_dict.project):
				vehicle_dict.project = sle.project

			# Move to delivered vehicles
			if vehicle_dict.qty <= 0:
				del vehicles_in_stock[key]
				vehicles_delivered.append(vehicle_dict)

		self.data = []

		for vehicle_dict in vehicles_delivered:
			if not vehicle_dict.delivery_date or not self.filters.from_date\
					or getdate(vehicle_dict.delivery_date) >= getdate(self.filters.from_date):
				self.data.append(vehicle_dict)

		for vehicle_dict in vehicles_in_stock.values():
			self.data.append(vehicle_dict)

	def prepare_data(self):
		for d in self.data:
			d.item_name = self.item_data.get(d.item_code, {}).get('item_name')
			d.disable_item_formatter = 1

			vehicle_data = self.vehicle_data.get(d.vehicle, frappe._dict())
			d.chassis_no = vehicle_data.chassis_no
			d.engine_no = vehicle_data.engine_no
			d.license_plate = vehicle_data.license_plate
			d.unregistered = vehicle_data.unregistered
			d.customer = vehicle_data.customer
			d.customer_name = vehicle_data.customer_name

			# Data from receipt
			if d.received_dt and d.received_dn:
				if d.received_dt == "Vehicle Receipt":
					vehicle_receipt_data = self.vehicle_receipt_data.get(d.received_dn, frappe._dict())
					if vehicle_receipt_data:
						d.chassis_no = vehicle_receipt_data.vehicle_chassis_no
						d.engine_no = vehicle_receipt_data.vehicle_engine_no
						d.license_plate = vehicle_receipt_data.vehicle_license_plate
						d.unregistered = vehicle_receipt_data.vehicle_unregistered
						d.vehicle_booking_order = vehicle_receipt_data.vehicle_booking_order
						d.customer = vehicle_receipt_data.customer
						d.customer_name = vehicle_receipt_data.customer_name

			# Data from delivery
			if d.delivery_dt and d.delivery_dn:
				if d.delivery_dt == "Vehicle Delivery":
					vehicle_delivery_data = self.vehicle_delivery_data.get(d.delivery_dn, frappe._dict())
					if vehicle_delivery_data:
						d.chassis_no = vehicle_delivery_data.vehicle_chassis_no or d.chassis_no
						d.engine_no = vehicle_delivery_data.vehicle_engine_no or d.engine_no
						d.license_plate = vehicle_delivery_data.vehicle_license_plate or d.license_plate
						d.unregistered = vehicle_delivery_data.vehicle_unregistered or d.unregistered
						d.vehicle_booking_order = vehicle_delivery_data.vehicle_booking_order or d.vehicle_booking_order
						d.customer = vehicle_delivery_data.customer
						d.customer_name = vehicle_delivery_data.customer_name

			# Booked Open Stock
			if not d.vehicle_booking_order and d.vehicle in self.booking_by_vehicle_data:
				booking_data = self.booking_by_vehicle_data[d.vehicle]
				d.vehicle_booking_order = booking_data.name
				d.open_stock = 1 if booking_data.vehicle_receipt else 0

			if d.vehicle_booking_order and not d.dispatch_date:
				d.dispatch_date = vehicle_data.get('dispatch_date')

			# Booking Customer Name
			if d.vehicle_booking_order and d.vehicle_booking_order in self.booking_by_booking_data:
				d.customer_name = self.booking_by_booking_data[d.vehicle_booking_order].get('customer_name')

			# Status
			if d.qty > 0:
				if d.vehicle_booking_order and d.open_stock:
					d.status = "Booked (Open Stock)"
					d.status_color = "purple"
				elif d.vehicle_booking_order:
					d.status = "Booked (In Stock)"
					d.status_color = "#743ee2"
				elif d.project:
					d.status = "For Repair"
					d.status_color = "orange"
				else:
					d.status = "Open Stock"
					d.status_color = "blue"
			elif d.qty <= 0:
				if d.delivery_dn:
					d.status = "Delivered"
					d.status_color = "green"
				elif d.dispatch_date and not d.received_date:
					if d.vehicle_booking_order:
						d.status = "Booked (Dispatched)"
					else:
						d.status = "Dispatched"

			# Mark Unregistered
			d.license_plate = 'Unregistered' if d.unregistered else d.license_plate

		self.data = sorted(self.data, key=lambda d: (not bool(d.received_date), cstr(d.received_date), cstr(d.dispatch_date)))

	def get_grouped_data(self):
		data = self.data

		self.group_by = []
		for i in range(3):
			group_label = self.filters.get("group_by_" + str(i + 1), "").replace("Group by ", "")

			if not group_label or group_label == "Ungrouped":
				continue
			elif group_label == "Item":
				group_field = "item_code"
			else:
				group_field = scrub(group_label)

			self.group_by.append(group_field)

		if not self.group_by:
			return data

		return group_report_data(data, self.group_by, calculate_totals=self.calculate_group_totals)

	def calculate_group_totals(self, data, group_field, group_value, grouped_by):
		totals = frappe._dict()

		# Copy grouped by into total row
		for f, g in grouped_by.items():
			totals[f] = g

		group_reference_doctypes = {
			"item_code": "Item"
		}

		reference_field = group_field[0] if isinstance(group_field, (list, tuple)) else group_field
		reference_dt = group_reference_doctypes.get(reference_field, unscrub(cstr(reference_field)))

		totals['vehicle'] = "'{0}: {1}'".format(reference_dt, grouped_by.get(reference_field))

		if 'item_code' in grouped_by:
			totals['item_name'] = data[0].item_name
			totals['disable_item_formatter'] = data[0].disable_item_formatter

		count = len(data)
		totals['code'] = "{0}".format(count)

		return totals

	def get_item_data(self):
		self.item_data = {}

		item_conditions = self.get_item_conditions()
		data = frappe.db.sql("""
			select name, item_name
			from `tabItem` item
			where is_vehicle = 1 {0}
		""".format(item_conditions), self.filters, as_dict=1)

		for d in data:
			self.item_data[d.name] = d

		return self.item_data

	def get_vehicle_data(self):
		self.vehicle_data = {}

		vehicle_names = list(set([d.vehicle for d in self.data]))
		if not vehicle_names:
			return self.vehicle_data

		data = frappe.db.sql("""
			select name, item_code, chassis_no, engine_no, license_plate, unregistered, dispatch_date
			from `tabVehicle`
			where name in %s
		""", [vehicle_names], as_dict=1)

		for d in data:
			self.vehicle_data[d.name] = d

		return self.vehicle_data

	def get_dispatched_vehicles(self):
		vehicle_names = list(set([d.vehicle for d in self.data]))

		exclude_condition = ""
		if vehicle_names:
			exclude_condition = " and name not in %(vehicle_names)s"

		date_condition = ""
		if self.filters.to_date:
			date_condition += " and dispatch_date <= %(to_date)s"

		self.dispatched_vehicles = frappe.db.sql("""
			select name as vehicle, item_code, 0 as qty, dispatch_date
			from `tabVehicle`
			where ifnull(dispatch_date, '') != '' and ifnull(purchase_document_no, '') = '' {0} {1}
		""".format(exclude_condition, date_condition),
			{'vehicle_names': vehicle_names, 'from_date': self.filters.from_date, 'to_date': self.filters.to_date},
			as_dict=1)

		for d in self.dispatched_vehicles:
			self.data.append(d)

	def get_vehicle_receipt_delivery_data(self):
		self.vehicle_receipt_data = {}
		self.vehicle_delivery_data = {}

		receipt_names = list(set([d.received_dn for d in self.data if d.received_dn and d.received_dt == "Vehicle Receipt"]))
		if receipt_names:
			data = frappe.db.sql("""
				select name, vehicle_booking_order, supplier, customer, customer_name, supplier_delivery_note,
					vehicle_chassis_no, vehicle_engine_no, vehicle_license_plate, vehicle_unregistered
				from `tabVehicle Receipt`
				where docstatus = 1 and name in %s
			""", [receipt_names], as_dict=1)

			for d in data:
				self.vehicle_receipt_data[d.name] = d

		delivery_names = list(set([d.delivery_dn for d in self.data if d.delivery_dn and d.delivery_dt == "Vehicle Delivery"]))
		if delivery_names:
			data = frappe.db.sql("""
				select name, vehicle_booking_order, customer, customer_name,
					vehicle_chassis_no, vehicle_engine_no, vehicle_license_plate, vehicle_unregistered
				from `tabVehicle Delivery`
				where docstatus = 1 and name in %s
			""", [delivery_names], as_dict=1)

			for d in data:
				self.vehicle_delivery_data[d.name] = d

	def get_booking_data(self):
		self.booking_by_vehicle_data = {}
		self.booking_by_booking_data = {}

		vehicle_names = list(set([d.vehicle for d in self.data]))
		if not vehicle_names:
			return {}

		data = frappe.db.sql("""
			select name, vehicle, vehicle_receipt, customer, customer_name
			from `tabVehicle Booking Order`
			where docstatus = 1 and vehicle in %s
		""", [vehicle_names], as_dict=1)

		for d in data:
			self.booking_by_booking_data[d.name] = d
			self.booking_by_vehicle_data[d.vehicle] = d

	def get_item_conditions(self):
		conditions = []

		if self.filters.item_code:
			conditions.append("item_code = %(item_code)s")

		if self.filters.brand:
			conditions.append("brand = %(brand)s")

		if self.filters.item_group:
			conditions.append(get_item_group_condition(self.filters.item_group))

		return "and {}".format(" and ".join(conditions)) if conditions else ""

	def get_sle_conditions(self):
		conditions = []

		if self.filters.item_codes:
			conditions.append("item_code in %(item_codes)s")

		if self.filters.warehouse:
			warehouse_details = frappe.db.get_value("Warehouse", self.filters.warehouse, ["lft", "rgt"], as_dict=1)
			if warehouse_details:
				conditions.append("exists (select name from `tabWarehouse` wh \
					where wh.lft >= {0} and wh.rgt <= {1} and `tabStock Ledger Entry`.warehouse = wh.name)"\
					.format(warehouse_details.lft, warehouse_details.rgt))

		return "and {}".format(" and ".join(conditions)) if conditions else ""

	def get_columns(self):
		return [
			{"label": _("Vehicle"), "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 100},
			{"label": _("Variant Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 100},
			{"label": _("Variant Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
			{"label": _("Chassis No"), "fieldname": "chassis_no", "fieldtype": "Data", "width": 150},
			{"label": _("Engine No"), "fieldname": "engine_no", "fieldtype": "Data", "width": 115},
			{"label": _("License Plate"), "fieldname": "license_plate", "fieldtype": "Data", "width": 100},
			{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 130},
			{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
			{"label": _("Booking #"), "fieldname": "vehicle_booking_order", "fieldtype": "Link", "options": "Vehicle Booking Order", "width": 100},
			{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 100},
			{"label": _("Dispatched"), "fieldname": "dispatch_date", "fieldtype": "Date", "width": 85},
			{"label": _("Received"), "fieldname": "received_date", "fieldtype": "Date", "width": 80},
			{"label": _("Delivered"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 80},
			{"label": _("Receipt Document"), "fieldname": "received_dn", "fieldtype": "Dynamic Link", "options": "received_dt", "width": 100},
			{"label": _("Delivery Document"), "fieldname": "delivery_dn", "fieldtype": "Dynamic Link", "options": "delivery_dt", "width": 100},
			{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
		]


def execute(filters=None):
	return VehicleStockReport(filters).run()
