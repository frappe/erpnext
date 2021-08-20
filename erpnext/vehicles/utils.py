import frappe
from frappe import _
from frappe.utils import getdate
from six import string_types


def validate_vehicle_item(item, validate_in_vehicle_booking=True):
	from erpnext.stock.doctype.item.item import validate_end_of_life
	validate_end_of_life(item.name, item.end_of_life, item.disabled)

	if not item.is_vehicle:
		frappe.throw(_("{0} is not a Vehicle Item").format(item.item_name or item.name))
	if validate_in_vehicle_booking and not item.include_in_vehicle_booking:
		frappe.throw(_("Vehicle Item {0} is not allowed for Vehicle Booking").format(item.item_name or item.name))


def get_booking_payments_by_order(vehicle_booking_orders, include_draft=False, payment_type=None):
	payment_entries = get_booking_payments(vehicle_booking_orders, include_draft, payment_type)

	payment_by_booking = {}
	for d in payment_entries:
		payment_by_booking.setdefault(d.vehicle_booking_order, []).append(d)

	return payment_by_booking


def get_advance_balance_details(booking_payment_entries):
	customer_payments, supplier_payments = separate_customer_and_supplier_payments(booking_payment_entries)
	advance_payments, balance_payments = separate_advance_and_balance_payments(customer_payments, supplier_payments)

	details = frappe._dict()
	if advance_payments:
		details.advance_payment_date = advance_payments[0].deposit_date
		details.advance_payment_amount = sum([d.amount for d in advance_payments])
	if balance_payments:
		details.balance_payment_date = balance_payments[-1].deposit_date
		details.balance_payment_amount = sum([d.amount for d in balance_payments])

	return details


def get_booking_payments(vehicle_booking_order, include_draft=False, payment_type=None):
	if not vehicle_booking_order:
		return []

	if isinstance(vehicle_booking_order, string_types):
		vehicle_booking_order = [vehicle_booking_order]

	docstatus_cond = "p.docstatus = 1"
	if include_draft:
		docstatus_cond = "p.docstatus < 2"

	payment_type_cond = ""
	if payment_type:
		payment_type_cond = "and p.payment_type = {0}".format(frappe.db.escape(payment_type))

	payment_entries = frappe.db.sql("""
		select p.name, p.posting_date, p.creation,
			p.vehicle_booking_order, p.party_type, p.party,
			p.payment_type, i.amount,
			i.instrument_type, i.instrument_title,
			i.instrument_no, i.instrument_date, i.bank,
			p.deposit_slip_no, p.deposit_type,
			i.name as row_id, i.vehicle_booking_payment_row
		from `tabVehicle Booking Payment Detail` i
		inner join `tabVehicle Booking Payment` p on p.name = i.parent
		where {0} and p.vehicle_booking_order in %s {1}
		order by i.instrument_date, p.posting_date, p.creation
	""".format(docstatus_cond, payment_type_cond), [vehicle_booking_order], as_dict=1)

	return payment_entries


def separate_customer_and_supplier_payments(payment_entries):
	customer_payments = []
	supplier_payments = []

	if payment_entries:
		customer_payments_by_row_id = {}

		for d in payment_entries:
			if d.payment_type == "Receive":
				customer_payments.append(d)
				customer_payments_by_row_id[d.row_id] = d

			if d.payment_type == "Pay":
				supplier_payments.append(d)
				d.deposit_doc_name = d.name
				d.deposit_date = d.posting_date

		for d in supplier_payments:
			if d.vehicle_booking_payment_row:
				customer_payment_row = customer_payments_by_row_id.get(d.vehicle_booking_payment_row)
				if customer_payment_row:
					customer_payment_row.deposit_slip_no = d.deposit_slip_no
					customer_payment_row.deposit_type = d.deposit_type
					customer_payment_row.deposit_doc_name = d.name
					customer_payment_row.deposit_date = d.posting_date

	customer_payments = sorted(customer_payments, key=lambda d: (d.instrument_date, d.posting_date, d.creation))
	supplier_payments = sorted(supplier_payments, key=lambda d: (d.posting_date, d.creation, d.idx))

	return customer_payments, supplier_payments


def separate_advance_and_balance_payments(customer_payments, supplier_payments):
	advance_payments = []
	balance_payments = []

	if customer_payments:
		if supplier_payments:
			first_deposit_date = getdate(supplier_payments[0].posting_date)

			for d in customer_payments:
				if d.deposit_date and getdate(d.deposit_date) <= first_deposit_date:
					advance_payments.append(d)
				else:
					balance_payments.append(d)
		else:
			advance_payments = customer_payments

	return advance_payments, balance_payments