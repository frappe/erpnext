# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from frappe.utils import flt, cstr, cint
from frappe.model.document import Document

instrument_copy_fields = ['instrument_type', 'instrument_date', 'instrument_no', 'bank', 'amount']

class VehicleBookingPayment(Document):
	def validate(self):
		self.validate_party_type()
		self.validate_vehicle_booking_order()
		self.validate_deposit_fields()
		self.set_undeposited()
		self.validate_undeposited_instruments()
		self.update_undeposited_instrument_details()
		self.validate_amounts()
		self.calculate_total_amount()
		self.set_party_name()
		self.set_title()

	def before_submit(self):
		self.validate_vehicle_booking_order_submitted()
		self.set_deposited()

	def on_submit(self):
		self.update_receiving_documents()
		self.update_vehicle_booking_order()

	def before_cancel(self):
		self.set_undeposited()

	def on_cancel(self):
		self.update_receiving_documents()
		self.update_vehicle_booking_order()

	def set_party_name(self):
		if not self.party_name:
			self.party_name = get_party_name(self.party_type, self.party, self.vehicle_booking_order)

	def set_title(self):
		self.title = self.party_name

	def validate_party_type(self):
		party_types_allowed_map = {
			"Receive": ['Customer'],
			"Pay": ['Supplier']
		}
		party_types_allowed = party_types_allowed_map.get(self.payment_type, [])

		if self.party_type not in party_types_allowed:
			frappe.throw(_("Party Type must be one of {0} for Payment Type {1}")
				.format(", ".format(party_types_allowed), self.payment_type))

	def validate_vehicle_booking_order(self):
		if self.vehicle_booking_order:
			vbo = frappe.db.get_value("Vehicle Booking Order", self.vehicle_booking_order,
				['docstatus', 'customer', 'financer', 'supplier'], as_dict=1)

			if not vbo:
				frappe.throw(_("Vehicle Booking Order {0} does not exist").format(self.vehicle_booking_order))

			if self.party_type == "Customer":
				if self.party not in (vbo.customer, vbo.financer):
					frappe.throw(_("Customer/Financer does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

			if self.party_type == "Supplier":
				if self.party != vbo.supplier:
					frappe.throw(_("Supplier does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

			if vbo.docstatus == 2:
				frappe.throw(_("Cannot make payment against {0} because it is cancelled")
					.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

	def validate_vehicle_booking_order_submitted(self):
		if self.vehicle_booking_order:
			docstatus = frappe.db.get_value("Vehicle Booking Order", self.vehicle_booking_order, 'docstatus')
			if docstatus != 1:
				frappe.throw(_("Cannot submit payment because {0} is not submitted. Please submit Vehicle Booking Order first")
					.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

	def validate_deposit_fields(self):
		if self.payment_type == "Pay":
			if not self.deposit_slip_no:
				frappe.throw(_("Deposit Slip No is mandatory for Payment Type 'Pay'"))
			if not self.deposit_type:
				frappe.throw(_("Deposit Type is mandatory for Payment Type 'Pay'"))

	def validate_amounts(self):
		for d in self.instruments:
			d.validate_value('amount', '>', 0)

	def calculate_total_amount(self):
		self.total_amount = 0
		for d in self.instruments:
			self.round_floats_in(d)
			self.total_amount += flt(d.amount)

		self.total_amount = flt(self.total_amount, self.precision('total_amount'))
		self.set_total_in_words()

	def set_total_in_words(self):
		from frappe.utils import money_in_words
		company_currency = erpnext.get_company_currency(self.company)
		self.in_words = money_in_words(self.total_amount, company_currency)

	def set_undeposited(self):
		if self.docstatus != 1:
			for d in self.instruments:
				d.deposited = 0

	def set_deposited(self):
		if self.payment_type != 'Pay':
			return

		for d in self.instruments:
			d.deposited = 1

	def validate_undeposited_instruments(self):
		if self.payment_type != "Pay":
			return

		vehicle_booking_payment_cache = {}

		for d in self.instruments:
			if d.vehicle_booking_payment and d.vehicle_booking_payment_row:
				if d.vehicle_booking_payment not in vehicle_booking_payment_cache:
					vehicle_booking_payment_cache[d.vehicle_booking_payment] = frappe.db.get_value("Vehicle Booking Payment",
						d.vehicle_booking_payment, ['docstatus', 'vehicle_booking_order', 'payment_type'], as_dict=1)

				payment_details = vehicle_booking_payment_cache[d.vehicle_booking_payment]

				if not payment_details:
					frappe.throw(_("Row #{0}: Vehicle Booking Payment {1} could not be found")
						.format(d.idx, d.vehicle_booking_payment))

				if payment_details.docstatus != 1:
					frappe.throw(_("Row #{0}: {1} is not submitted")
						.format(d.idx, frappe.get_desk_link("Vehicle Booking Payment", d.vehicle_booking_payment)))

				if payment_details.payment_type != 'Receive':
					frappe.throw(_("Row #{0}: {1} is not a received payment")
						.format(d.idx, frappe.get_desk_link("Vehicle Booking Payment", d.vehicle_booking_payment)))

				if cstr(payment_details.vehicle_booking_order) != cstr(self.vehicle_booking_order):
					frappe.throw(_("Row #{0}: Vehicle Booking Order does not match the undeposited instrument in {1}")
						.format(d.idx, frappe.get_desk_link("Vehicle Booking Payment", d.vehicle_booking_payment)))

				self.get_is_deposited(d, throw=True)
			else:
				frappe.throw(_("Row #{0}: Instrument is not linked to a valid undeposited Vehicle Booking Payment")
					.format(d.idx))

	def get_is_deposited(self, d, exclude_self=True, throw=False):
		exclude = ""
		if exclude_self and not self.is_new():
			exclude = " and p.name != {0}".format(frappe.db.escape(self.name))

		is_deposited = frappe.db.sql_list("""
			select distinct p.name
			from `tabVehicle Booking Payment Detail` i
			inner join `tabVehicle Booking Payment` p on p.name = i.parent
			where p.docstatus = 1 and p.payment_type = 'Pay'
				and i.vehicle_booking_payment = %s and i.vehicle_booking_payment_row = %s {0}
		""".format(exclude), [d.vehicle_booking_payment, d.vehicle_booking_payment_row])

		if is_deposited and throw:
			frappe.throw(_("Row #{0}: Instrument in {1} is already deposited in {2}")
				.format(d.idx, frappe.get_desk_link("Vehicle Booking Payment", d.vehicle_booking_payment),
					frappe.get_desk_link("Vehicle Booking Payment", is_deposited[0])))

		return is_deposited

	def update_undeposited_instrument_details(self):
		if self.payment_type != "Pay":
			return

		for d in self.instruments:
			if d.vehicle_booking_payment and d.vehicle_booking_payment_row:
				instrument_details = frappe.db.get_value("Vehicle Booking Payment Detail", d.vehicle_booking_payment_row,
					instrument_copy_fields, as_dict=1)

				if not instrument_details:
					frappe.throw(_("Row #{0}: Could not find undeposited Vehicle Booking Payment in {1}")
						.format(d.idx, frappe.get_desk_link("Vehicle Booking Payment", d.vehicle_booking_payment)))

				d.update(instrument_details)

	def update_receiving_documents(self):
		if self.payment_type != "Pay":
			return

		for d in self.instruments:
			frappe.db.set_value("Vehicle Booking Payment Detail", d.vehicle_booking_payment_row, "deposited",
				cint(bool(self.get_is_deposited(d, exclude_self=False))))

	def update_vehicle_booking_order(self):
		pass


@frappe.whitelist()
def get_party_name(party_type, party, vehicle_booking_order=None):
	from erpnext.accounts.party import get_party_name

	party_name = None

	if vehicle_booking_order:
		if party_type == "Customer":
			party_name = frappe.db.get_value("Vehicle Booking Order", vehicle_booking_order, 'customer_name')
		elif party_type == "Supplier":
			party_name = frappe.db.get_value("Vehicle Booking Order", vehicle_booking_order, 'supplier_name')
	else:
		party_name = get_party_name(party_type, party)

	return party_name


@frappe.whitelist()
def get_vehicle_booking_party(vehicle_booking_order, party_type):
	vbo = frappe.db.get_value("Vehicle Booking Order", vehicle_booking_order,
		['customer', 'financer', 'supplier'], as_dict=1)

	if party_type == "Customer":
		return vbo.financer or vbo.customer
	elif party_type == "Supplier":
		return vbo.supplier


@frappe.whitelist()
def get_undeposited_instruments(vehicle_booking_order):
	fields = ", ".join(["i.`{0}`".format(f) for f in instrument_copy_fields])

	instruments = frappe.db.sql("""
		select p.name as vehicle_booking_payment, i.name as vehicle_booking_payment_row, {0}
		from `tabVehicle Booking Payment Detail` i
		inner join `tabVehicle Booking Payment` p on p.name = i.parent
		where p.docstatus = 1 and p.payment_type = 'Receive' and p.vehicle_booking_order = %s
			and not exists(select dep.name from `tabVehicle Booking Payment Detail` dep
				where dep.docstatus = 1 and dep.vehicle_booking_payment_row = i.name)
	""".format(fields), vehicle_booking_order, as_dict=1)

	if not instruments:
		frappe.msgprint(_("No undeposited instruments found against {0}")
			.format(frappe.get_desk_link("Vehicle Booking Order", vehicle_booking_order)), indicator='orange')

	return instruments
