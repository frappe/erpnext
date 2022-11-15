# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub, unscrub
from frappe.utils import cint, cstr, flt
from erpnext.vehicles.utils import get_booking_payments_by_order, get_advance_balance_details
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
from frappe.desk.query_report import group_report_data


class VehicleBookingSummaryReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

		self.buckets = {}

		self.sum_fields = [
			'invoice_total',
			'customer_advance', 'supplier_advance',
			'undeposited_amount', 'payment_adjustment',
			'customer_outstanding', 'supplier_outstanding',
			'advance_payment_amount', 'balance_payment_amount',
		]

		self.count_fields = [
			'qty_booked', 'qty_cancelled', 'qty_expired', 'qty_allocated', 'qty_priority',
			'qty_vehicle_received', 'qty_vehicle_delivered', 'qty_vehicle_in_stock',
			'qty_invoice_received', 'qty_invoice_delivered', 'qty_invoice_in_hand',
		]

		self.show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"

	def run(self):
		self.get_data()
		self.prepare_data()

		data = self.get_grouped_data()
		columns = self.get_columns()

		return columns, data

	def get_data(self):
		allocation_conditions = self.get_conditions('allocation')
		booking_conditions = self.get_conditions('booking')

		self.allocation_data = frappe.db.sql("""
			select m.name as vehicle_allocation, m.item_code, m.supplier, m.allocation_period, m.delivery_period,
				m.is_additional, item.variant_of, item.brand, item.item_group,
				ap.from_date as allocation_from_date, dp.from_date as delivery_from_date, m.is_expired
			from `tabVehicle Allocation` m
			inner join `tabItem` item on item.name = m.item_code
			inner join `tabVehicle Allocation Period` ap on ap.name = m.allocation_period
			inner join `tabVehicle Allocation Period` dp on dp.name = m.delivery_period
			left join `tabVehicle Booking Order` vbo on m.name = vbo.vehicle_allocation and vbo.docstatus = 1
			where m.docstatus = 1 {conditions}
		""".format(conditions=allocation_conditions), self.filters, as_dict=1)

		self.booking_data = frappe.db.sql("""
			select m.name as vehicle_booking_order, m.item_code,
				m.supplier, m.delivery_period, alloc.allocation_period, alloc.is_additional, m.priority,
				m.vehicle_delivered_date, m.vehicle_received_date, m.invoice_delivered_date, m.invoice_received_date,
				m.invoice_total, m.customer_advance, m.supplier_advance, m.customer_advance - m.supplier_advance as undeposited_amount,
				m.payment_adjustment, m.customer_outstanding, m.supplier_outstanding,
				item.variant_of, item.brand, item.item_group,
				m.vehicle_allocation_required, m.vehicle_allocation, m.status,
				ap.from_date as allocation_from_date, dp.from_date as delivery_from_date
			from `tabVehicle Booking Order` m
			inner join `tabItem` item on item.name = m.item_code
			left join `tabVehicle Allocation` alloc on alloc.name = m.vehicle_allocation
			left join `tabVehicle Allocation Period` ap on ap.name = alloc.allocation_period
			left join `tabVehicle Allocation Period` dp on dp.name = m.delivery_period
			where m.docstatus = 1 {0}
		""".format(booking_conditions), self.filters, as_dict=1)

	def prepare_data(self):
		for d in self.allocation_data:
			bucket = self.get_bucket(d)
			bucket.qty_allocated += 1

			if cint(d.is_expired):
				bucket.qty_expired += 1

		self.set_payment_details()

		for d in self.booking_data:
			if not d.vehicle_allocation:
				if d.vehicle_allocation_required:
					d.allocation_period = "'Unassigned'"
				else:
					d.allocation_period = "'Not Applicable'"

			bucket = self.get_bucket(d)

			bucket.qty_booked += 1

			if cint(d.status == "Cancelled Booking"):
				bucket.qty_cancelled += 1

			if cint(d.get('priority')):
				bucket.qty_priority += 1

			if d.get('vehicle_delivered_date'):
				bucket.qty_vehicle_delivered += 1

			if d.get('vehicle_received_date'):
				bucket.qty_vehicle_received += 1
				if not d.get('vehicle_delivered_date'):
					bucket.qty_vehicle_in_stock += 1

			if d.get('invoice_delivered_date'):
				bucket.qty_invoice_delivered += 1

			if d.get('invoice_received_date'):
				bucket.qty_invoice_received += 1
				if not d.get('invoice_delivered_date'):
					bucket.qty_invoice_in_hand += 1

			for f in self.sum_fields:
				bucket[f] += flt(d.get(f))

		self.data = sorted(self.buckets.values(), key=lambda d: (
			d.variant_of or d.item_code,
			d.item_code,
			cstr(d.delivery_from_date),
			cstr(d.allocation_from_date),
			cint(d.is_additional),
		))

		return self.data

	def get_bucket(self, d):
		key = (d.item_code, cstr(d.delivery_period), cstr(d.allocation_period), cint(d.is_additional))
		if key not in self.buckets:
			template = frappe._dict({
				'reference_type': 'Item', 'reference': d.item_code,
				'variant_of': d.variant_of, 'item_code': d.item_code,
				'delivery_period': d.delivery_period, 'delivery_from_date': d.delivery_from_date,
				'allocation_period': d.allocation_period, 'allocation_from_date': d.allocation_from_date,
				'is_additional': cint(d.is_additional), 'supplier': d.supplier,
			})
			for f in self.sum_fields + self.count_fields:
				template[f] = 0

			self.buckets[key] = template

		return self.buckets[key]

	def set_payment_details(self):
		booking_numbers = list(set([d.vehicle_booking_order for d in self.booking_data if d.vehicle_booking_order]))
		self.payments_by_order = get_booking_payments_by_order(booking_numbers)

		for d in self.booking_data:
			booking_payment_entries = self.payments_by_order.get(d.vehicle_booking_order) or []
			d.update(get_advance_balance_details(booking_payment_entries))

	def get_grouped_data(self):
		data = self.data

		self.group_by = [None]
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

		if len(self.group_by) <= 1:
			return data

		return group_report_data(data, self.group_by, calculate_totals=self.calculate_group_totals,
			postprocess_group=self.postprocess_group)

	def calculate_group_totals(self, data, group_field, group_value, grouped_by):
		totals = frappe._dict()

		# Copy grouped by into total row
		for f, g in grouped_by.items():
			totals[f] = g

		# Sum
		for f in self.sum_fields + self.count_fields:
			totals[f] = sum([flt(d.get(f)) for d in data])

		group_reference_doctypes = {
			"item_code": "Item",
			"variant_of": "Item",
			"allocation_period": "Vehicle Allocation Period",
			"delivery_period": "Vehicle Allocation Period",
		}

		reference_field = group_field[0] if isinstance(group_field, (list, tuple)) else group_field
		reference_dt = group_reference_doctypes.get(reference_field, unscrub(cstr(reference_field)))
		totals['reference_type'] = reference_dt
		if not group_field:
			totals['reference'] = "'Total'"
		elif not reference_dt:
			totals['reference'] = "'{0}'".format(grouped_by.get(reference_field))
		else:
			totals['reference'] = grouped_by.get(reference_field)

		# set item_code from model
		if "item_code" not in grouped_by and "variant_of" in grouped_by:
			totals['item_code'] = totals['variant_of']

		totals['disable_item_formatter'] = cint(self.show_item_name)

		if 'allocation_period' in grouped_by:
			totals['allocation_from_date'] = data[0].allocation_from_date
		if 'delivery_period' in grouped_by:
			totals['delivery_from_date'] = data[0].delivery_from_date

		return totals

	def postprocess_group(self, group_object, grouped_by):
		# sort child period groups
		group_object.allocation_from_date = group_object.totals.allocation_from_date
		group_object.delivery_from_date = group_object.totals.delivery_from_date

		if group_object.rows[0].group_field == 'allocation_period':
			group_object.rows = sorted(group_object.rows, key=lambda d: cstr(d.allocation_from_date))
		elif group_object.rows[0].group_field == 'delivery_period':
			group_object.rows = sorted(group_object.rows, key=lambda d: cstr(d.delivery_from_date))

	def get_conditions(self, cond_type):
		conditions = []

		if self.filters.company:
			conditions.append("m.company = %(company)s")

		if self.filters.from_allocation_period:
			self.filters.allocation_from_date = frappe.get_cached_value("Vehicle Allocation Period", self.filters.from_allocation_period, "from_date")
			conditions.append("ap.from_date >= %(allocation_from_date)s")

		if self.filters.to_allocation_period:
			self.filters.allocation_to_date = frappe.get_cached_value("Vehicle Allocation Period", self.filters.to_allocation_period, "to_date")
			conditions.append("ap.to_date <= %(allocation_to_date)s")

		if self.filters.from_delivery_period:
			self.filters.delivery_from_date = frappe.get_cached_value("Vehicle Allocation Period", self.filters.from_delivery_period, "from_date")
			conditions.append("dp.from_date >= %(delivery_from_date)s")

		if self.filters.to_delivery_period:
			self.filters.delivery_to_date = frappe.get_cached_value("Vehicle Allocation Period", self.filters.to_delivery_period, "to_date")
			conditions.append("dp.to_date <= %(delivery_to_date)s")

		if self.filters.variant_of:
			conditions.append("item.variant_of = %(variant_of)s")

		if self.filters.item_code:
			if cond_type == 'booking':
				conditions.append("(m.item_code = %(item_code)s or m.previous_item_code = %(item_code)s)")
			else:
				conditions.append("(m.item_code = %(item_code)s or vbo.item_code = %(item_code)s or vbo.previous_item_code = %(item_code)s)")

		if self.filters.vehicle_color:
			if cond_type == 'booking':
				conditions.append("""(m.vehicle_color = %(vehicle_color)s
					or (m.color_1 = %(vehicle_color)s and ifnull(m.vehicle_color, '') = ''))""")
			else:
				conditions.append("""(m.vehicle_color = %(vehicle_color)s
					or vbo.vehicle_color = %(vehicle_color)s or vbo.previous_color = %(vehicle_color)s
					or (vbo.color_1 = %(vehicle_color)s and ifnull(vbo.vehicle_color, '') = ''))""")

		if self.filters.item_group:
			conditions.append(get_item_group_condition(self.filters.item_group))

		if self.filters.brand:
			conditions.append("item.brand = %(brand)s")

		if self.filters.customer:
			if cond_type == 'booking':
				conditions.append("m.customer = %(customer)s")
			else:
				conditions.append("vbo.customer = %(customer)s")

		if self.filters.financer:
			if cond_type == 'booking':
				conditions.append("m.financer = %(financer)s")
			else:
				conditions.append("vbo.financer = %(financer)s")

		if self.filters.supplier:
			conditions.append("m.supplier = %(supplier)s")

		if self.filters.priority:
			if cond_type == 'booking':
				conditions.append("m.priority = 1")
			else:
				conditions.append("vbo.priority = 1")

		out = " and ".join(conditions)
		out = "and {}".format(out) if conditions else ""
		return out

	def get_columns(self):
		columns = []

		if self.group_by:
			columns.append({"label": _("Reference/Item"), "fieldname": "reference", "fieldtype": "Dynamic Link",
				"options": "reference_type", "width": 180})

		columns += [
			{"label": _("Delivery Period"), "fieldname": "delivery_period", "fieldtype": "Link", "options": "Vehicle Allocation Period", "width": 110},
			{"label": _("Allocation Period"), "fieldname": "allocation_period", "fieldtype": "Link", "options": "Vehicle Allocation Period", "width": 120},
			{"label": _("Additional"), "fieldname": "is_additional", "fieldtype": "Check", "width": 55},
			{"label": _("Allocated"), "fieldname": "qty_allocated", "fieldtype": "Int", "width": 75},
			{"label": _("Expired"), "fieldname": "qty_expired", "fieldtype": "Int", "width": 65},
			{"label": _("Booked"), "fieldname": "qty_booked", "fieldtype": "Int", "width": 65},
			{"label": _("Cancelled"), "fieldname": "qty_cancelled", "fieldtype": "Int", "width": 77},
			{"label": _("Priority"), "fieldname": "qty_priority", "fieldtype": "Int", "width": 65},
			{"label": _("V. Received"), "fieldname": "qty_vehicle_received", "fieldtype": "Int", "width": 85},
			{"label": _("V. Delivered"), "fieldname": "qty_vehicle_delivered", "fieldtype": "Int", "width": 90},
			{"label": _("V. In Stock"), "fieldname": "qty_vehicle_in_stock", "fieldtype": "Int", "width": 85},
			{"label": _("Inv. Received"), "fieldname": "qty_invoice_received", "fieldtype": "Int", "width": 95},
			{"label": _("Inv. Delivered"), "fieldname": "qty_invoice_delivered", "fieldtype": "Int", "width": 99},
			{"label": _("Inv. In Hand"), "fieldname": "qty_invoice_in_hand", "fieldtype": "Int", "width": 85},
			{"label": _("Invoice Total"), "fieldname": "invoice_total", "fieldtype": "Currency", "width": 120},
			{"label": _("Payment Received"), "fieldname": "customer_advance", "fieldtype": "Currency", "width": 120},
			{"label": _("Payment Deposited"), "fieldname": "supplier_advance", "fieldtype": "Currency", "width": 120},
			{"label": _("Undeposited Amount"), "fieldname": "undeposited_amount", "fieldtype": "Currency", "width": 120},
			{"label": _("Payment Adjustment"), "fieldname": "payment_adjustment", "fieldtype": "Currency", "width": 120},
			{"label": _("Customer Outstanding"), "fieldname": "customer_outstanding", "fieldtype": "Currency", "width": 120},
			{"label": _("Supplier Outstanding"), "fieldname": "supplier_outstanding", "fieldtype": "Currency", "width": 120},
			{"label": _("Advance Payment Amount"), "fieldname": "advance_payment_amount", "fieldtype": "Currency", "width": 120},
			{"label": _("Balance Payment Amount"), "fieldname": "balance_payment_amount", "fieldtype": "Currency", "width": 120},
			{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Data", "width": 100},
		]

		return columns


def execute(filters=None):
	return VehicleBookingSummaryReport(filters).run()
