# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub, unscrub
from frappe.utils import cint, cstr
from erpnext.selling.doctype.vehicle_booking_order.vehicle_booking_order import get_booking_payments
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
from frappe.desk.query_report import group_report_data


class VehicleAllocationRegisterReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

	def run(self):
		self.get_data()
		self.prepare_data()
		columns = self.get_columns()

		data = self.get_grouped_data()

		return columns, data

	def get_data(self):
		allocation_conditions = self.get_conditions('allocation')
		booking_conditions = self.get_conditions('booking')

		vbo_join = "left join `tabVehicle Booking Order` vbo on m.name = vbo.vehicle_allocation" \
			if self.filters.customer or self.filters.financer else ""

		allocation_data = frappe.db.sql("""
			select m.name as vehicle_allocation, m.item_code, m.supplier, m.allocation_period, m.delivery_period,
				m.sr_no, m.code, m.is_additional, m.booking_price, m.vehicle_color,
				ap.from_date as allocation_from_date, dp.from_date as delivery_from_date
			from `tabVehicle Allocation` m
			inner join `tabItem` item on item.name = m.item_code
			inner join `tabVehicle Allocation Period` ap on ap.name = m.allocation_period
			inner join `tabVehicle Allocation Period` dp on dp.name = m.delivery_period
			{vbo_join}
			where m.docstatus = 1 and item.vehicle_allocation_required = 1 {conditions}
			order by ap.from_date, m.item_code, m.is_additional, m.sr_no
		""".format(conditions=allocation_conditions, vbo_join=vbo_join), self.filters, as_dict=1)

		booking_data = frappe.db.sql("""
			select m.name as vehicle_booking_order, m.item_code, m.supplier, m.allocation_period, m.delivery_period,
				m.vehicle_allocation, m.transaction_date,
				m.color_1, m.color_2, m.color_3,
				m.customer, m.financer, m.customer_name, m.finance_type, m.tax_id, m.tax_cnic,
				m.contact_person, m.contact_mobile, m.contact_phone,
				ap.from_date as allocation_from_date, dp.from_date as delivery_from_date
			from `tabVehicle Booking Order` m
			inner join `tabItem` item on item.name = m.item_code
			left join `tabVehicle Allocation Period` ap on ap.name = m.allocation_period
			left join `tabVehicle Allocation Period` dp on dp.name = m.delivery_period
			where m.docstatus = 1 and item.vehicle_allocation_required = 1 {0}
		""".format(booking_conditions), self.filters, as_dict=1)

		self.allocation_to_row = {}
		for d in allocation_data:
			self.allocation_to_row[d.vehicle_allocation] = d

		unallocated_bookings = []
		for d in booking_data:
			if d.vehicle_allocation in self.allocation_to_row:
				self.allocation_to_row[d.vehicle_allocation].update(d)
			else:
				unallocated_bookings.append(d)
				d.code = 'Unassigned'

		self.data = unallocated_bookings + allocation_data
		return self.data

	def prepare_data(self):
		self.get_payment_data()

		for d in self.data:
			if d.vehicle_allocation:
				d.reference_type = 'Vehicle Allocation'
				d.reference = d.vehicle_allocation or "'Unassigned'"
			else:
				d.reference_type = 'Vehicle Booking Order'
				d.reference = d.vehicle_booking_order
				d.allocation_period = None

			is_leased = d.financer and d.finance_type == "Leased"

			d.vehicle_color = d.vehicle_color or d.color_1 or d.color_2 or d.color_3
			d.tax_cnic_ntn = d.tax_id or d.tax_cnic if is_leased else d.tax_cnic or d.tax_id
			d.contact_number = d.contact_mobile or d.contact_phone

			if d.vehicle_booking_order in self.customer_payments:
				d.customer_payment_date = self.customer_payments[d.vehicle_booking_order][0].instrument_date

			if d.vehicle_booking_order in self.supplier_payments:
				d.supplier_payment_date = self.supplier_payments[d.vehicle_booking_order][0].posting_date

		self.data = sorted(self.data, key=lambda d: (
			bool(d.vehicle_allocation),
			cstr(d.allocation_from_date) if d.allocation_from_date else cstr(d.delivery_from_date),
			d.item_code,
			d.code,
			cint(d.is_additional),
			d.sr_no,
			cstr(d.transaction_date)
		))

		return self.data

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
			"item_code": "Item",
			"allocation_period": "Vehicle Allocation Period",
			"delivery_period": "Vehicle Allocation Period",
		}

		reference_field = group_field[0] if isinstance(group_field, (list, tuple)) else group_field
		reference_dt = group_reference_doctypes.get(reference_field, unscrub(cstr(reference_field)))
		totals['reference_type'] = reference_dt
		totals['reference'] = grouped_by.get(reference_field)

		if totals.get('reference_type') == "Vehicle Allocation Period" and not totals.get('reference'):
			totals['reference'] = "'Unassigned'"

		count = len(data)
		booked = len([d for d in data if d.vehicle_booking_order])
		if 'allocation_period' in grouped_by and not totals.get('allocation_period'):
			totals['code'] = "Unassigned: {0}".format(count)
		else:
			totals['code'] = "Tot: {0}, Bkd: {1}, Avl: {2}".format(count, booked, count-booked)

		return totals

	def get_conditions(self, cond_type):
		conditions = []

		if self.filters.company:
			conditions.append("m.company = %(company)s")

		if self.filters.from_allocation_period:
			self.filters.allocation_from_date = frappe.get_cached_value("Vehicle Allocation Period", self.filters.from_allocation_period, "from_date")
			conditions.append("ap.from_date >= %(allocation_from_date)s")

		if self.filters.to_allocation_period:
			self.filters.allocation_to_date = frappe.get_cached_value("Vehicle Allocation Period", self.filters.to_allocation_period, "to_date")
			conditions.append("ap.to_date <= %(allocation_from_date)s")

		if self.filters.from_delivery_period:
			self.filters.delivery_from_date = frappe.get_cached_value("Vehicle Allocation Period", self.filters.from_delivery_period, "from_date")
			conditions.append("dp.from_date >= %(delivery_from_date)s")

		if self.filters.to_delivery_period:
			self.filters.delivery_to_date = frappe.get_cached_value("Vehicle Allocation Period", self.filters.to_delivery_period, "to_date")
			conditions.append("dp.to_date <= %(delivery_to_date)s")

		if self.filters.item_code:
			conditions.append("m.item_code = %(item_code)s")

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

		return "and {}".format(" and ".join(conditions)) if conditions else ""


	def get_payment_data(self):
		booking_numbers = list(set([d.vehicle_booking_order for d in self.data if d.vehicle_booking_order]))
		payment_entries = get_booking_payments(booking_numbers)

		self.customer_payments = {}
		self.supplier_payments = {}

		for d in payment_entries:
			if d.party_type == "Customer":
				self.customer_payments.setdefault(d.vehicle_booking_order, []).append(d)

			if d.party_type == "Supplier":
				self.supplier_payments.setdefault(d.vehicle_booking_order, []).append(d)


	def get_columns(self):
		return [
			{"label": _("Reference"), "fieldname": "reference", "fieldtype": "Dynamic Link", "options": "reference_type", "width": 160},
			{"label": _("Sr #"), "fieldname": "sr_no", "fieldtype": "Int", "width": 45},
			{"label": _("Allocation Code"), "fieldname": "code", "fieldtype": "Data", "width": 140},
			{"label": _("Additional"), "fieldname": "is_additional", "fieldtype": "Check", "width": 60},
			{"label": _("Allocation Period"), "fieldname": "allocation_period", "fieldtype": "Link", "options": "Vehicle Allocation Period", "width": 120},
			{"label": _("Delivery Period"), "fieldname": "delivery_period", "fieldtype": "Link", "options": "Vehicle Allocation Period", "width": 110},
			{"label": _("Variant Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
			{"label": _("Booking Price"), "fieldname": "booking_price", "fieldtype": "Data", "width": 100},
			{"label": _("Color"), "fieldname": "vehicle_color", "fieldtype": "Link", "options": "Vehicle Color", "width": 120},
			{"label": _("Booking #"), "fieldname": "vehicle_booking_order", "fieldtype": "Link", "options": "Vehicle Booking Order", "width": 100},
			{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
			# {"label": _("Customer (User)"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 100},
			# {"label": _("Financer"), "fieldname": "financer", "fieldtype": "Link", "options": "Customer", "width": 100},
			{"label": _("CNIC/NTN"), "fieldname": "tax_cnic_ntn", "fieldtype": "Data", "width": 110},
			{"label": _("Contact"), "fieldname": "contact_number", "fieldtype": "Data", "width": 110},
			{"label": _("Booking Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
			{"label": _("Instrument Date"), "fieldname": "customer_payment_date", "fieldtype": "Date", "width": 100},
			{"label": _("Deposit Date"), "fieldname": "supplier_payment_date", "fieldtype": "Date", "width": 100},
			{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 100},
		]


def execute(filters=None):
	return VehicleAllocationRegisterReport(filters).run()
