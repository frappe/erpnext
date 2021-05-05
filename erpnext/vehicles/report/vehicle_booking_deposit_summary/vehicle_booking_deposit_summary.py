# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub, unscrub
from frappe.utils import getdate, nowdate, cstr, flt
from erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order import get_booking_payments
from frappe.desk.query_report import group_report_data


class VehicleBookingDepositSummaryReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

	def run(self):
		self.get_data()
		self.prepare_data()
		columns = self.get_columns()

		data = self.get_grouped_data()

		return columns, data

	def get_data(self):
		conditions = self.get_conditions()

		self.data = frappe.db.sql("""
			select
				dep_m.name as deposit_doc, rec_m.name as receipt_doc,
				dep_m.posting_date as deposit_date, rec_m.posting_date as receipt_date, dep_i.instrument_date,
				dep_i.amount, dep_m.total_amount, dep_i.instrument_no, dep_i.bank, dep_m.deposit_slip_no,
				rec_m.party_name as customer_name, dep_m.vehicle_booking_order,
				vbo.tax_id, vbo.tax_cnic, vbo.finance_type,
				vbo.item_code, item.item_name, item.variant_of,
				vbo.allocation_period, vbo.delivery_period,
				vbo.invoice_total
			from `tabVehicle Booking Payment Detail` dep_i
			inner join `tabVehicle Booking Payment` dep_m on dep_m.name = dep_i.parent
			inner join `tabVehicle Booking Payment Detail` rec_i on rec_i.name = dep_i.vehicle_booking_payment_row
				and rec_i.parent = dep_i.vehicle_booking_payment
			inner join `tabVehicle Booking Payment` rec_m on rec_m.name = rec_i.parent
			inner join `tabVehicle Booking Order` vbo on vbo.name = dep_m.vehicle_booking_order
			inner join `tabItem` item on item.name = vbo.item_code
			left join `tabVehicle Allocation Period` ap on ap.name = vbo.allocation_period
			left join `tabVehicle Allocation Period` dp on dp.name = vbo.delivery_period
			where dep_m.docstatus = 1 {0}
			order by deposit_date, deposit_slip_no, dep_i.idx
		""".format(conditions), self.filters, as_dict=1)

		vehicle_booking_orders = list(set([d.vehicle_booking_order for d in self.data]))
		booking_payment_data = get_booking_payments(vehicle_booking_orders, payment_type="Pay")

		self.payment_by_booking = {}
		for d in booking_payment_data:
			self.payment_by_booking.setdefault(d.vehicle_booking_order, []).append(d)

		for vbo in self.payment_by_booking.keys():
			self.payment_by_booking[vbo] = sorted(self.payment_by_booking[vbo], key=lambda d: (d.deposit_date, d.creation))

		return self.data

	def prepare_data(self):
		dealership_code = frappe.get_cached_value("Vehicles Settings", None, "dealership_code")

		for d in self.data:
			d.reference_type = "Vehicle Booking Payment"
			d.reference = d.deposit_doc

			if d.finance_type == "Leased":
				d.tax_cnic_ntn = d.tax_id
			else:
				d.tax_cnic_ntn = d.tax_cnic or d.tax_id

			d.dealership_code = dealership_code
			d.disable_item_formatter = 1

			all_deposits = self.payment_by_booking.get(d.vehicle_booking_order, [])

			# Is first deposit?
			is_first_deposit = False
			first_deposit_doc = None
			if all_deposits:
				first_deposit_doc = all_deposits[0].name

			if d.deposit_doc == first_deposit_doc:
				is_first_deposit = True

			# Is full payment?
			is_full_payment = d.total_amount == d.invoice_total

			if is_first_deposit:
				if is_full_payment:
					d.deposit_stage = "Full & Final"
				else:
					d.deposit_stage = "Advance"
			else:
				d.deposit_stage = "Balance"

		return self.data

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

		return group_report_data(data, self.group_by, calculate_totals=self.calculate_group_totals)

	def calculate_group_totals(self, data, group_field, group_value, grouped_by):
		totals = frappe._dict()

		# Copy grouped by into total row
		for f, g in grouped_by.items():
			totals[f] = g

		# Sum
		sum_fields = ['amount']
		for f in sum_fields:
			totals[f] = sum([flt(d.get(f)) for d in data])

		group_reference_doctypes = {
			"item_code": "Item",
			"variant_of": "Item",
			"allocation_period": "Vehicle Allocation Period",
			"delivery_period": "Vehicle Allocation Period",
		}

		# set reference field
		reference_field = group_field[0] if isinstance(group_field, (list, tuple)) else group_field
		reference_dt = group_reference_doctypes.get(reference_field, unscrub(cstr(reference_field)))
		totals['reference_type'] = reference_dt
		totals['reference'] = grouped_by.get(reference_field)

		# set item code when grouped by model
		if "variant_of" in grouped_by:
			totals['item_code'] = totals['variant_of']

		return totals

	def get_conditions(self):
		conditions = []

		if self.filters.company:
			conditions.append("dep_m.company = %(company)s")

		if self.filters.from_date:
			conditions.append("dep_m.posting_date >= %(from_date)s")

		if self.filters.to_date:
			conditions.append("dep_m.posting_date <= %(to_date)s")

		if self.filters.supplier:
			conditions.append("dep_m.party_type = 'Supplier' and dep_m.party = %(party)s")

		if self.filters.deposit_type:
			conditions.append("dep_m.deposit_type = %(deposit_type)s")

		if self.filters.variant_of:
			conditions.append("item.variant_of = %(variant_of)s")

		if self.filters.item_code:
			conditions.append("item.name = %(item_code)s")

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

		return "and {}".format(" and ".join(conditions)) if conditions else ""

	def get_columns(self):
		return [
			{"label": _("Reference"), "fieldname": "reference", "fieldtype": "Dynamic Link", "options": "reference_type", "width": 100},
			{"label": _("Instrument Date"), "fieldname": "instrument_date", "fieldtype": "Date", "width": 90},
			{"label": _("Receipt Date"), "fieldname": "receipt_date", "fieldtype": "Date", "width": 90},
			{"label": _("Deposit Date"), "fieldname": "deposit_date", "fieldtype": "Date", "width": 90},
			{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 100},
			{"label": _("Instrument #"), "fieldname": "instrument_no", "fieldtype": "Data", "width": 110},
			{"label": _("Bank"), "fieldname": "bank", "fieldtype": "Link", "options": "Bank", "width": 110},
			{"label": _("Deposit Slip"), "fieldname": "deposit_slip_no", "fieldtype": "Data", "width": 90},
			{"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
			{"label": _("CNIC/NTN"), "fieldname": "tax_cnic_ntn", "fieldtype": "Data", "width": 110},
			{"label": _("Dealer Code"), "fieldname": "dealership_code", "fieldtype": "Data", "width": 90},
			{"label": _("Booking #"), "fieldname": "vehicle_booking_order", "fieldtype": "Link", "options": "Vehicle Booking Order", "width": 105},
			{"label": _("Variant Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
			{"label": _("Variant Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
			{"label": _("Advance/Balance"), "fieldname": "deposit_stage", "fieldtype": "Data", "width": 120},
			{"label": _("Allocation Period"), "fieldname": "allocation_period", "fieldtype": "Link", "options": "Vehicle Allocation Period", "width": 120},
			{"label": _("Delivery Period"), "fieldname": "delivery_period", "fieldtype": "Link", "options": "Vehicle Allocation Period", "width": 110},
			{"label": _("Receipt Document"), "fieldname": "receipt_doc", "fieldtype": "Link", "options": "Vehicle Booking Payment", "width": 100},
		]


def execute(filters=None):
	return VehicleBookingDepositSummaryReport(filters).run()
