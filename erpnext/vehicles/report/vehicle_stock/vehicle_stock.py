# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub, unscrub
from frappe.utils import flt, cstr, getdate, cint
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
from frappe.desk.query_report import group_report_data


class VehicleStockReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.to_date = getdate(self.filters.to_date)

		if getdate(self.filters.from_date) > self.filters.to_date:
			frappe.throw(_("From Date cannot be after To Date"))

		# Vehicle Status filter
		self.filters.exclude_in_stock = 0
		self.filters.exclude_delivered = 0
		self.filters.exclude_dispatched = 0
		if self.filters.status == "In Stock Vehicles":
			self.filters.exclude_delivered = 1
			self.filters.exclude_dispatched = 1
		elif self.filters.status == "Dispatched Vehicles":
			self.filters.exclude_in_stock = 1
			self.filters.exclude_delivered = 1
		elif self.filters.status == "In Stock and Dispatched Vehicles":
			self.filters.exclude_delivered = 1
		elif self.filters.status == "Delivered Vehicles":
			self.filters.exclude_in_stock = 1
			self.filters.exclude_dispatched = 1

	def run(self):
		self.get_item_data()
		self.get_stock_ledger_entries()
		self.process_sle()
		self.get_dispatched_vehicles()
		self.get_vehicle_data()
		self.get_vehicle_receipt_delivery_data()
		self.get_vehicle_invoice_data()
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
		self.vehicle_stock_map = {}
		vehicles_in_stock = {}
		vehicles_delivered = []

		empty_vehicle_dict = frappe._dict({
			"qty": 0,
		})

		for sle in self.sle:
			key = (sle.item_code, sle.serial_no)

			vehicle_dict = vehicles_in_stock.setdefault(key, empty_vehicle_dict.copy())
			self.vehicle_stock_map[key] = vehicle_dict

			# Item Code, Warehouse and Vehicle
			vehicle_dict.item_code = sle.item_code
			vehicle_dict.vehicle = sle.serial_no
			vehicle_dict.warehouse = sle.warehouse

			# In Stock or not
			vehicle_dict.qty = flt(vehicle_dict.qty + sle.actual_qty, 0)

			# Receiving and Delivery
			if sle.voucher_type != 'Vehicle Movement':
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
			if vehicle_dict.qty <= 0 and sle.voucher_type != 'Vehicle Movement':
				del vehicles_in_stock[key]
				vehicles_delivered.append(vehicle_dict)

		self.data = []

		# Delivered Vehicles
		if not self.filters.get('exclude_delivered'):
			for vehicle_dict in vehicles_delivered:
				in_date_range = not vehicle_dict.delivery_date or not self.filters.from_date\
					or getdate(vehicle_dict.delivery_date) >= getdate(self.filters.from_date)

				if in_date_range:
					self.data.append(vehicle_dict)

		# In Stock Vehicles
		if not self.filters.get('exclude_in_stock'):
			for vehicle_dict in vehicles_in_stock.values():
				self.data.append(vehicle_dict)

	def prepare_data(self):
		for d in self.data:
			variant_data = self.item_data.get(d.item_code, frappe._dict())
			model_data = self.item_data.get(variant_data.variant_of, frappe._dict())

			d.item_name = variant_data.item_name
			d.item_group = variant_data.item_group
			d.brand = variant_data.brand

			d.variant_of = variant_data.variant_of
			d.variant_of_name = model_data.item_name

			d.disable_item_formatter = 1

			vehicle_data = self.vehicle_data.get(d.vehicle, frappe._dict())
			d.chassis_no = vehicle_data.chassis_no
			d.engine_no = vehicle_data.engine_no
			d.license_plate = vehicle_data.license_plate
			d.unregistered = vehicle_data.unregistered
			d.color = vehicle_data.color
			d.customer = vehicle_data.customer
			d.customer_name = vehicle_data.customer_name
			d.has_return = 0
			d.has_delivery_return = 0
			d.has_receipt_return = 0
			d.open_stock = 0

			# Data from receipt
			if d.received_dt and d.received_dn:
				vehicle_receipt_data = None
				if d.received_dt == "Vehicle Receipt":
					vehicle_receipt_data = self.vehicle_receipt_data.get(d.received_dn, frappe._dict())
				elif d.received_dt == "Vehicle Delivery":
					vehicle_receipt_data = self.vehicle_delivery_data.get(d.received_dn, frappe._dict())

				if vehicle_receipt_data:
					d.chassis_no = vehicle_receipt_data.vehicle_chassis_no
					d.engine_no = vehicle_receipt_data.vehicle_engine_no
					d.license_plate = vehicle_receipt_data.vehicle_license_plate or d.license_plate
					d.unregistered = vehicle_receipt_data.vehicle_unregistered or d.unregistered
					d.color = vehicle_receipt_data.vehicle_color or d.color
					d.odometer = cint(vehicle_receipt_data.vehicle_odometer) or None
					d.vehicle_booking_order = vehicle_receipt_data.vehicle_booking_order
					d.customer = vehicle_receipt_data.customer
					d.customer_name = vehicle_receipt_data.customer_name
					d.supplier = vehicle_receipt_data.supplier
					d.supplier_name = vehicle_receipt_data.supplier_name
					d.transporter = vehicle_receipt_data.transporter
					d.transporter_name = vehicle_receipt_data.transporter_name or vehicle_receipt_data.transporter
					d.lr_no = vehicle_receipt_data.lr_no
					d.receipt_remarks = vehicle_receipt_data.remarks
					d.has_return = cint(vehicle_receipt_data.is_return) or d.has_return
					d.has_delivery_return = cint(vehicle_receipt_data.is_return)

			# Data from delivery
			if d.delivery_dt and d.delivery_dn:
				vehicle_delivery_data = None
				if d.delivery_dt == "Vehicle Delivery":
					vehicle_delivery_data = self.vehicle_delivery_data.get(d.delivery_dn, frappe._dict())
				elif d.delivery_dt == "Vehicle Receipt":
					vehicle_delivery_data = self.vehicle_receipt_data.get(d.delivery_dn, frappe._dict())

				if vehicle_delivery_data:
					d.chassis_no = vehicle_delivery_data.vehicle_chassis_no or d.chassis_no
					d.engine_no = vehicle_delivery_data.vehicle_engine_no or d.engine_no
					d.license_plate = vehicle_delivery_data.vehicle_license_plate or d.license_plate
					d.unregistered = vehicle_delivery_data.vehicle_unregistered or d.unregistered
					d.color = vehicle_delivery_data.vehicle_color or d.color
					d.odometer = cint(vehicle_delivery_data.vehicle_odometer) or d.odometer
					d.vehicle_booking_order = vehicle_delivery_data.vehicle_booking_order or d.vehicle_booking_order
					d.customer = vehicle_delivery_data.customer
					d.customer_name = vehicle_delivery_data.booking_customer_name or vehicle_delivery_data.customer_name
					d.broker = vehicle_delivery_data.broker
					d.broker_name = vehicle_delivery_data.broker_name
					d.receiver_contact = vehicle_delivery_data.receiver_contact
					d.delivered_to = vehicle_delivery_data.receiver_contact_display or vehicle_delivery_data.customer_name
					d.delivered_to_contact = vehicle_delivery_data.receiver_contact_mobile or vehicle_delivery_data.receiver_contact_phone
					d.has_return = cint(vehicle_delivery_data.is_return) or d.has_return
					d.has_receipt_return = cint(vehicle_delivery_data.is_return)

					if vehicle_delivery_data.vehicle_owner and vehicle_delivery_data.vehicle_owner != vehicle_delivery_data.customer:
						d.delivery_customer = vehicle_delivery_data.customer
						d.delivery_customer_name = vehicle_delivery_data.customer_name

			# Booked Open Stock / Dispatched Vehicle Booking
			if not d.vehicle_booking_order and d.vehicle in self.booking_by_vehicle_data:
				booking_data = self.booking_by_vehicle_data[d.vehicle]
				if not d.received_dn:
					d.vehicle_booking_order = booking_data.name
				elif d.received_dt == "Vehicle Receipt" and d.received_dn == booking_data.vehicle_receipt:
					d.vehicle_booking_order = booking_data.name
					d.open_stock = 1

			# Unbooked Open Stock
			if not d.vehicle_booking_order:
				d.open_stock = 1

			if d.vehicle_booking_order and not d.dispatch_date:
				d.dispatch_date = vehicle_data.get('dispatch_date')

			# Booking Data
			if d.vehicle_booking_order and d.vehicle_booking_order in self.booking_by_booking_data:
				booking_data = self.booking_by_booking_data[d.vehicle_booking_order]
				d.customer = d.customer or booking_data.get('customer')
				d.financer = booking_data.get('financer')
				d.customer_name = booking_data.get('customer_name')
				d.lessee_name = booking_data.get('lessee_name')
				d.supplier = d.supplier or booking_data.get('supplier')
				d.supplier_name = d.supplier_name or booking_data.get('supplier_name')
				d.contact_number = booking_data.get('contact_mobile') or booking_data.get('contact_phone')
				d.is_leased = booking_data.get('financer') and booking_data.get('finance_type') == "Leased"
				d.finance_type = booking_data.get('finance_type') if booking_data.get('financer') else None

				d.delivery_period = booking_data.get('delivery_period')
				d.delivery_due_date = booking_data.get('delivery_date')

			# Invoice Receipt Data
			if d.vehicle in self.vehicle_invoice_receipt_data:
				invoice_data = self.vehicle_invoice_receipt_data[d.vehicle]
				d.bill_no = invoice_data.get('bill_no')
				d.bill_date = invoice_data.get('bill_date')
				d.invoice_received_date = invoice_data.get('posting_date')

			# Invoice Movement Data
			if d.vehicle in self.vehicle_invoice_movement_data:
				for invoice_data in self.vehicle_invoice_movement_data[d.vehicle]:
					if invoice_data.purpose in ['Issue', 'Return']:
						d.invoice_issued_for = invoice_data.get('issued_for')

					if invoice_data.purpose == "Issue":
						d.invoice_issue_date = invoice_data.get('posting_date')
					elif invoice_data.purpose == "Return":
						d.invoice_return_date = invoice_data.get('posting_date')

			# Invoice Delivery Data
			if d.vehicle in self.vehicle_invoice_delivery_data:
				invoice_data = self.vehicle_invoice_delivery_data[d.vehicle]
				d.invoice_delivery_date = invoice_data.get('posting_date')

			# User Name
			d.user_name = d.lessee_name or d.delivery_customer_name

			# Age
			if d.received_date:
				d.age = (getdate(self.filters.to_date) - getdate(d.received_date)).days or 0

			# Warehouse Name
			if d.warehouse:
				d.warehouse_name = frappe.db.get_value("Warehouse", d.warehouse, 'warehouse_name', cache=1)

			# Stock Status
			if d.qty > 0:
				if d.vehicle_booking_order and not d.open_stock:
					d.status = "In Stock"
					d.status_color = "#743ee2"
				else:
					d.status = "Open Stock"
					d.status_color = "purple" if d.vehicle_booking_order else "blue"

				if d.has_delivery_return:
					d.status += " (Returned)"
			elif d.qty <= 0:
				if d.delivery_dn:
					d.status = "Returned" if d.has_receipt_return else "Delivered"
					d.status_color = "red" if d.has_receipt_return else "green"
				elif d.dispatch_date and not d.received_date:
					d.status = "Dispatched"
					d.status_color = "orange"

			# Invoice Status
			if d.invoice_delivery_date:
				d.invoice_status = "Delivered"
				d.invoice_status_color = "green"
			elif d.invoice_received_date:
				was_issued = d.invoice_issue_date and getdate(d.invoice_issue_date) >= getdate(d.invoice_received_date)
				was_returned = d.invoice_issue_date and d.invoice_return_date and getdate(d.invoice_return_date) >= getdate(d.invoice_issue_date)
				if was_issued and not was_returned:
					d.invoice_status = "Issued{0}".format(" For {0}".format(d.invoice_issued_for) if d.invoice_issued_for else "")
					d.invoice_status_color = "purple"
				else:
					d.invoice_status = "In Hand"
					d.invoice_status_color = "orange"

		self.data = self.filter_rows(self.data)
		self.data = sorted(self.data, key=lambda d: (not bool(d.received_date), cstr(d.received_date), cstr(d.dispatch_date)))

	def filter_rows(self, data):
		if self.filters.customer:
			data = [d for d in data if d.customer == self.filters.customer]
		if self.filters.financer:
			data = [d for d in data if d.financer == self.filters.financer]
		if self.filters.vehicle_owner:
			data = [d for d in data if (d.financer == self.filters.vehicle_owner if d.is_leased else d.customer == self.filters.vehicle_owner)]
		if self.filters.broker:
			data = [d for d in data if d.broker == self.filters.broker]

		if self.filters.supplier:
			data = [d for d in data if d.supplier == self.filters.supplier]

		if self.filters.vehicle_booking_order:
			data = [d for d in data if d.vehicle_booking_order == self.filters.vehicle_booking_order]

		if self.filters.vehicle_color:
			data = [d for d in data if d.color == self.filters.vehicle_color]

		if self.filters.invoice_status == "Invoice In Hand and Delivered":
			data = [d for d in data if d.invoice_received_date or d.invoice_delivery_date]
		elif self.filters.invoice_status == "Invoice In Hand":
			data = [d for d in data if d.invoice_received_date and not d.invoice_delivery_date]
		elif self.filters.invoice_status == "Invoice Issued":
			was_issued = lambda d: d.invoice_issue_date and getdate(d.invoice_issue_date) >= getdate(d.invoice_received_date)
			was_returned = lambda d: d.invoice_issue_date and d.invoice_return_date and getdate(d.invoice_return_date) >= getdate(d.invoice_issue_date)
			data = [d for d in data if was_issued(d) and not was_returned(d)]
		elif self.filters.invoice_status == "Invoice Delivered":
			data = [d for d in data if d.invoice_delivery_date]
		elif self.filters.invoice_status == "Invoice Not Received":
			data = [d for d in data if not d.invoice_received_date and not d.invoice_delivery_date]

		return data

	def get_grouped_data(self):
		data = self.data

		self.group_by = []
		for i in range(3):
			group_label = self.filters.get("group_by_" + str(i + 1), "").replace("Group by ", "")

			if not group_label or group_label == "Ungrouped":
				continue
			elif group_label == "Variant":
				group_field = "item_code"
			elif group_label == "Model":
				group_field = "variant_of"
			else:
				group_field = scrub(group_label)

			self.group_by.append(group_field)

		if not self.group_by:
			return data

		return group_report_data(data, self.group_by,
			calculate_totals=self.calculate_group_totals, postprocess_group=self.postprocess_group)

	def calculate_group_totals(self, data, group_field, group_value, grouped_by):
		totals = frappe._dict()

		# Copy grouped by into total row
		for f, g in grouped_by.items():
			totals[f] = g

		group_reference_doctypes = {
			"item_code": "Item",
			"variant_of": "Item",
		}

		reference_field = group_field[0] if isinstance(group_field, (list, tuple)) else group_field
		reference_dt = group_reference_doctypes.get(reference_field, unscrub(cstr(reference_field)))

		totals['vehicle'] = "'{0}: {1}'".format(reference_dt, grouped_by.get(reference_field))

		if 'item_code' in grouped_by:
			totals['item_name'] = data[0].item_name
			totals['disable_item_formatter'] = data[0].disable_item_formatter

		if 'variant_of' in grouped_by:
			totals['variant_of_name'] = data[0].variant_of_name
			totals['disable_item_formatter'] = data[0].disable_item_formatter

		status_counts = {}
		for d in data:
			status_counts.setdefault(d.status, 0)
			status_counts[d.status] += 1

		status_counts_text = ", ".join(["{0}: {1}".format(status, frappe.format(count))\
			for status, count in status_counts.items()])

		total_text = ""
		if len(status_counts) > 1:
			total_count = len(data)
			total_text = "Total: {0}".format(frappe.format(total_count))

		totals['status'] = "{0}{1}{2}".format(total_text, ", " if total_text and status_counts_text else "", status_counts_text)

		return totals

	def postprocess_group(self, group_object, grouped_by):
		group_object.item_name = group_object.totals.item_name
		group_object.variant_of_name = group_object.totals.variant_of_name

	def get_item_data(self):
		self.item_data = {}

		item_conditions = self.get_item_conditions()
		variant_data = frappe.db.sql("""
			select name, item_name, variant_of, item_group, brand
			from `tabItem` item
			where is_vehicle = 1 {0}
		""".format(item_conditions), self.filters, as_dict=1)

		model_item_codes = list(set([d.variant_of for d in variant_data if d.variant_of]))
		if model_item_codes:
			model_data = frappe.db.sql("""
				select name, item_name, variant_of, item_group, brand
				from `tabItem` item
				where name in %s
			""", [model_item_codes], as_dict=1)

			for d in model_data:
				self.item_data[d.name] = d

		for d in variant_data:
			self.item_data[d.name] = d

		return self.item_data

	def get_vehicle_data(self):
		self.vehicle_data = {}

		vehicle_names = list(set([d.vehicle for d in self.data]))
		if not vehicle_names:
			return self.vehicle_data

		data = frappe.db.sql("""
			select name, item_code, chassis_no, engine_no, license_plate, color, unregistered,
				dispatch_date, last_odometer
			from `tabVehicle`
			where name in %s
		""", [vehicle_names], as_dict=1)

		for d in data:
			self.vehicle_data[d.name] = d

		return self.vehicle_data

	def get_dispatched_vehicles(self):
		if self.filters.get('exclude_dispatched'):
			return

		vehicle_names = list(set([d.vehicle for d in self.vehicle_stock_map.values()]))

		args = self.filters.copy()
		item_conditions = self.get_item_conditions()

		exclude_condition = ""
		if vehicle_names:
			exclude_condition = " and v.name not in %(vehicle_names)s"
			args['vehicle_names'] = vehicle_names

		date_condition = ""
		if self.filters.to_date:
			date_condition += " and v.dispatch_date <= %(to_date)s"

		vehicle_condition = ""
		if self.filters.vehicle:
			vehicle_condition = " and v.name = %(vehicle)s"

		self.dispatched_vehicles = frappe.db.sql("""
			select v.name as vehicle, v.item_code, 0 as qty, v.dispatch_date
			from `tabVehicle` v
			inner join `tabItem` item on v.item_code = item.name
			where ifnull(v.dispatch_date, '') != '' {0} {1} {2} {3}
		""".format(item_conditions, exclude_condition, date_condition, vehicle_condition), args, as_dict=1)

		for d in self.dispatched_vehicles:
			self.data.append(d)

	def get_vehicle_receipt_delivery_data(self):
		self.vehicle_receipt_data = {}
		self.vehicle_delivery_data = {}

		receipt_names = [d.received_dn for d in self.data if d.received_dn and d.received_dt == "Vehicle Receipt"]
		receipt_names += [d.delivery_dn for d in self.data if d.delivery_dn and d.delivery_dt == "Vehicle Receipt"]
		receipt_names = list(set(receipt_names))
		if receipt_names:
			data = frappe.db.sql("""
				select name, vehicle_booking_order, supplier, supplier_name, customer, customer_name,
					vehicle_chassis_no, vehicle_engine_no, vehicle_license_plate, vehicle_unregistered, vehicle_color,
					transporter, transporter_name, lr_no, is_return, vehicle_odometer, remarks
				from `tabVehicle Receipt`
				where docstatus = 1 and name in %s
			""", [receipt_names], as_dict=1)

			for d in data:
				self.vehicle_receipt_data[d.name] = d

		delivery_names = [d.delivery_dn for d in self.data if d.delivery_dn and d.delivery_dt == "Vehicle Delivery"]
		delivery_names += [d.received_dn for d in self.data if d.received_dn and d.received_dt == "Vehicle Delivery"]
		delivery_names = list(set(delivery_names))
		if delivery_names:
			data = frappe.db.sql("""
				select name, vehicle_booking_order,
					customer, customer_name, booking_customer_name, broker, broker_name, vehicle_owner, vehicle_owner_name,
					vehicle_chassis_no, vehicle_engine_no, vehicle_license_plate, vehicle_unregistered, vehicle_color,
					receiver_contact, receiver_contact_display, receiver_contact_mobile, receiver_contact_phone,
					transporter, transporter_name, lr_no, is_return, vehicle_odometer
				from `tabVehicle Delivery`
				where docstatus = 1 and name in %s
			""", [delivery_names], as_dict=1)

			for d in data:
				self.vehicle_delivery_data[d.name] = d

	def get_vehicle_invoice_data(self):
		self.vehicle_invoice_receipt_data = {}
		self.vehicle_invoice_movement_data = {}
		self.vehicle_invoice_delivery_data = {}

		vehicle_names = list(set([d.vehicle for d in self.data]))
		if not vehicle_names:
			return

		args = self.filters.copy()
		args['vehicle_names'] = vehicle_names

		date_condition = ""
		if self.filters.to_date:
			date_condition += " and posting_date <= %(to_date)s"

		receipt_data = frappe.db.sql("""
			select name, vehicle, posting_date, bill_no, bill_date
			from `tabVehicle Invoice`
			where docstatus = 1 and vehicle in %(vehicle_names)s {0}
		""".format(date_condition), args, as_dict=1)

		for d in receipt_data:
			self.vehicle_invoice_receipt_data[d.vehicle] = d

		movement_data = frappe.db.sql("""
			select trn.name, d.vehicle, trn.posting_date, trn.purpose, trn.issued_for
			from `tabVehicle Invoice Movement Detail` d
			inner join `tabVehicle Invoice Movement` trn on trn.name = d.parent
			where trn.docstatus = 1 and trn.purpose in ('Issue', 'Return') and d.vehicle in %(vehicle_names)s {0}
			order by trn.posting_date, trn.creation
		""".format(date_condition), args, as_dict=1)

		for d in movement_data:
			self.vehicle_invoice_movement_data.setdefault(d.vehicle, []).append(d)

		delivery_data = frappe.db.sql("""
			select name, vehicle, posting_date
			from `tabVehicle Invoice Delivery`
			where docstatus = 1 and is_copy = 0 and vehicle in %(vehicle_names)s {0}
			order by posting_date desc, creation desc
		""".format(date_condition), args, as_dict=1)

		for d in delivery_data:
			self.vehicle_invoice_delivery_data[d.vehicle] = d

	def get_booking_data(self):
		self.booking_by_vehicle_data = {}
		self.booking_by_booking_data = {}

		vehicle_names = list(set([d.vehicle for d in self.data]))
		if not vehicle_names:
			return

		data = frappe.db.sql("""
			select name, vehicle, vehicle_receipt,
				customer, financer, finance_type,
				customer_name, lessee_name,
				supplier, supplier_name,
				contact_mobile, contact_phone,
				delivery_period, delivery_date
			from `tabVehicle Booking Order`
			where docstatus = 1 and vehicle in %s
		""", [vehicle_names], as_dict=1)

		for d in data:
			self.booking_by_booking_data[d.name] = d
			self.booking_by_vehicle_data[d.vehicle] = d

	def get_item_conditions(self):
		conditions = []

		if self.filters.item_code:
			conditions.append("item.item_code = %(item_code)s")

		if self.filters.variant_of:
			conditions.append("item.variant_of = %(variant_of)s")

		if self.filters.brand:
			conditions.append("item.brand = %(brand)s")

		if self.filters.item_group:
			conditions.append(get_item_group_condition(self.filters.item_group))

		return "and {0}".format(" and ".join(conditions)) if conditions else ""

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

		if self.filters.vehicle:
			conditions.append("serial_no = %(vehicle)s")

		return "and {}".format(" and ".join(conditions)) if conditions else ""

	def get_columns(self):
		columns = [
			{"label": _("Vehicle"), "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 100},
			{"label": _("Variant Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
			# {"label": _("Variant Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
			{"label": _("Color"), "fieldname": "color", "fieldtype": "Link", "options": "Vehicle Color", "width": 120},
			{"label": _("Chassis No"), "fieldname": "chassis_no", "fieldtype": "Data", "width": 150},
			{"label": _("Engine No"), "fieldname": "engine_no", "fieldtype": "Data", "width": 115},
			{"label": _("Reg No"), "fieldname": "license_plate", "fieldtype": "Data", "width": 70},
			{"label": _("Odometer"), "fieldname": "odometer", "fieldtype": "Int", "width": 60},
			{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
			{"label": _("Age"), "fieldname": "age", "fieldtype": "Int", "width": 50},
			{"label": _("Booking #"), "fieldname": "vehicle_booking_order", "fieldtype": "Link", "options": "Vehicle Booking Order", "width": 105},
			{"label": _("Delivery Period"), "fieldname": "delivery_period", "fieldtype": "Link", "options": "Vehicle Allocation Period", "width": 110},
			{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
			{"label": _("User/Lessee Name"), "fieldname": "user_name", "fieldtype": "Data", "width": 130},
			{"label": _("Contact"), "fieldname": "contact_number", "fieldtype": "Data", "width": 110},
			{"label": _("Delivered To"), "fieldname": "delivered_to", "fieldtype": "Data", "width": 110},

			{"label": _("Broker Name"), "fieldname": "broker_name", "fieldtype": "Data", "width": 110},
			{"label": _("Supplier"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 110},
			{"label": _("Receipt Remarks"), "fieldname": "receipt_remarks", "fieldtype": "Data", "width": 150},
			{"label": _("Transporter"), "fieldname": "transporter_name", "fieldtype": "Data", "width": 110},
			{"label": _("Bilty"), "fieldname": "lr_no", "fieldtype": "Data", "width": 70},
			{"label": _("Invoice"), "fieldname": "bill_no", "fieldtype": "Data", "width": 80},
			{"label": _("Inv Status"), "fieldname": "invoice_status", "fieldtype": "Data", "width": 80},
			{"label": _("Dispatched"), "fieldname": "dispatch_date", "fieldtype": "Date", "width": 85},
			{"label": _("Received"), "fieldname": "received_date", "fieldtype": "Date", "width": 80},
			{"label": _("Delivered"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 80},
			{"label": _("Receipt Document"), "fieldname": "received_dn", "fieldtype": "Dynamic Link", "options": "received_dt", "width": 100},
			{"label": _("Delivery Document"), "fieldname": "delivery_dn", "fieldtype": "Dynamic Link", "options": "delivery_dt", "width": 100},
			{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
		]

		return columns


def execute(filters=None):
	return VehicleStockReport(filters).run()
