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
		self.get_vehicle_data()
		self.get_vehicle_booking_order_data()
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
		vehicle_map = {}

		empty_vehicle_dict = frappe._dict({
			"qty": 0,
		})

		for sle in self.sle:
			key = (sle.item_code, sle.serial_no)

			# Item Code, Warehouse and Vehicle
			vehicle_dict = vehicle_map.setdefault(key, empty_vehicle_dict.copy())
			vehicle_dict.item_code = sle.item_code
			vehicle_dict.vehicle = sle.serial_no
			vehicle_dict.warehouse = sle.warehouse

			# In Stock or not
			vehicle_dict.qty = flt(vehicle_dict.qty + sle.actual_qty, 0)

			# Receiving and Delivery Date
			if sle.actual_qty > 0:
				vehicle_dict.received_date = sle.posting_date
				vehicle_dict.delivery_date = None
			else:
				vehicle_dict.delivery_date = sle.posting_date

			# Project
			if sle.actual_qty > 0 or (sle.actual_qty < 0 and not vehicle_dict.project):
				vehicle_dict.project = sle.project

		self.data = []
		for vehicle_dict in vehicle_map.values():
			# skip delivered vehicle outside of date range
			if not vehicle_dict.qty and vehicle_dict.delivery_date and vehicle_dict.delivery_date < getdate(self.filters.from_date):
				continue

			self.data.append(vehicle_dict)

	def prepare_data(self):
		for d in self.data:
			d.item_name = self.item_data.get(d.item_code, {}).get('item_name')
			d.disable_item_formatter = 1

			vehicle_data = self.vehicle_data.get(d.vehicle, frappe._dict())
			d.chassis_no = vehicle_data.chassis_no
			d.engine_no = vehicle_data.engine_no
			d.license_plate = 'Unregistered' if vehicle_data.unregistered else vehicle_data.license_plate

			booking_data = self.booking_data.get(d.vehicle, frappe._dict())
			d.vehicle_booking_order = booking_data.name

			if d.qty > 0:
				d.status = "In Stock"
			elif d.qty == 0 and d.delivery_date:
				d.status = "Delivered"

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

		# group_reference_doctypes = {
		# 	"item_code": "Item"
		# }
		#
		# reference_field = group_field[0] if isinstance(group_field, (list, tuple)) else group_field
		# reference_dt = group_reference_doctypes.get(reference_field, unscrub(cstr(reference_field)))
		# totals['reference_type'] = reference_dt
		# totals['reference'] = grouped_by.get(reference_field)

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
			select name, item_code, chassis_no, engine_no, license_plate, unregistered
			from `tabVehicle`
			where name in %s
		""", [vehicle_names], as_dict=1)

		for d in data:
			self.vehicle_data[d.name] = d

		return self.vehicle_data

	def get_vehicle_booking_order_data(self):
		self.booking_data = {}

		vehicle_names = list(set([d.vehicle for d in self.data]))
		if not vehicle_names:
			return self.booking_data

		data = frappe.db.sql("""
			select name, vehicle
			from `tabVehicle Booking Order`
			where docstatus = 1 and vehicle in %s
		""", [vehicle_names], as_dict=1)

		for d in data:
			self.booking_data[d.vehicle] = d

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
			{"label": _("Variant Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
			{"label": _("Variant Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
			{"label": _("Vehicle"), "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 100},
			{"label": _("Chassis No"), "fieldname": "chassis_no", "fieldtype": "Data", "width": 150},
			{"label": _("Engine No"), "fieldname": "engine_no", "fieldtype": "Data", "width": 115},
			{"label": _("License Plate"), "fieldname": "license_plate", "fieldtype": "Data", "width": 100},
			{"label": _("Received"), "fieldname": "received_date", "fieldtype": "Date", "width": 100},
			{"label": _("Delivered"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 100},
			{"label": _("Booking Order"), "fieldname": "vehicle_booking_order", "fieldtype": "Link", "options": "Vehicle Booking Order", "width": 110},
			{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 100},
			{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
			{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
		]


def execute(filters=None):
	return VehicleStockReport(filters).run()
