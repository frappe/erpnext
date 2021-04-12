# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order import get_booking_payments


class VehicleBookingDepositSummaryReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

	def run(self):
		self.get_data()
		data = self.prepare_data()
		columns = self.get_columns()

		return columns, data

	def get_data(self):
		conditions = self.get_conditions()

		self.data = frappe.db.sql("""
			select
				dep_m.name as deposit_doc, rec_m.name as receipt_doc,
				dep_m.posting_date as deposit_date, rec_m.posting_date as receipt_date,
				dep_i.amount, dep_m.total_amount, dep_i.instrument_no, dep_i.bank, dep_m.deposit_slip_no,
				rec_m.party_name as customer_name, dep_m.vehicle_booking_order,
				vbo.tax_id, vbo.tax_cnic, vbo.finance_type, vbo.item_code, i.item_name,
				vbo.invoice_total
			from `tabVehicle Booking Payment Detail` dep_i
			inner join `tabVehicle Booking Payment` dep_m on dep_m.name = dep_i.parent
			inner join `tabVehicle Booking Payment Detail` rec_i on rec_i.name = dep_i.vehicle_booking_payment_row
				and rec_i.parent = dep_i.vehicle_booking_payment
			inner join `tabVehicle Booking Payment` rec_m on rec_m.name = rec_i.parent
			inner join `tabVehicle Booking Order` vbo on vbo.name = dep_m.vehicle_booking_order
			inner join `tabItem` i on i.name = vbo.item_code
			where dep_m.docstatus = 1 {0}
			order by deposit_date, deposit_slip_no, receipt_date
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
			if d.finance_type == "Leased":
				d.tax_cnic_ntn = d.tax_id
			else:
				d.tax_cnic_ntn = d.tax_cnic or d.tax_id

			d.dealership_code = dealership_code

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

		return "and {}".format(" and ".join(conditions)) if conditions else ""

	def get_columns(self):
		return [
			{"label": _("Deposit Document"), "fieldname": "deposit_doc", "fieldtype": "Link", "options": "Vehicle Booking Payment", "width": 90},
			{"label": _("Receipt Document"), "fieldname": "receipt_doc", "fieldtype": "Link", "options": "Vehicle Booking Payment", "width": 90},
			{"label": _("Receipt Date"), "fieldname": "receipt_date", "fieldtype": "Date", "width": 90},
			{"label": _("Deposit Date"), "fieldname": "deposit_date", "fieldtype": "Date", "width": 90},
			{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 100},
			{"label": _("Instrument #"), "fieldname": "instrument_no", "fieldtype": "Data", "width": 110},
			{"label": _("Bank"), "fieldname": "bank", "fieldtype": "Link", "options": "Bank", "width": 110},
			{"label": _("Deposit Slip"), "fieldname": "deposit_slip_no", "fieldtype": "Data", "width": 90},
			{"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
			{"label": _("CNIC/NTN"), "fieldname": "tax_cnic_ntn", "fieldtype": "Data", "width": 100},
			{"label": _("Dealer Code"), "fieldname": "dealership_code", "fieldtype": "Data", "width": 90},
			{"label": _("Booking #"), "fieldname": "vehicle_booking_order", "fieldtype": "Link", "options": "Vehicle Booking Order", "width": 105},
			{"label": _("Variant Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 100},
			{"label": _("Variant Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
			{"label": _("Advance/Balance"), "fieldname": "deposit_stage", "fieldtype": "Data", "width": 150},
		]


def execute(filters=None):
	return VehicleBookingDepositSummaryReport(filters).run()
