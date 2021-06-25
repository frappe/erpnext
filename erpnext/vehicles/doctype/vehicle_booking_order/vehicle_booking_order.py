# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today
from frappe.model.naming import set_name_by_naming_series
from erpnext.vehicles.doctype.vehicle_allocation.vehicle_allocation import get_allocation_title
from erpnext.vehicles.vehicle_booking_controller import VehicleBookingController
from six import string_types


class VehicleBookingOrder(VehicleBookingController):
	def get_feed(self):
		customer = self.get('company') if self.customer_is_company else self.get('customer') or self.get('financer')
		return _("For {0} | {1}").format(self.get("customer_name") or customer, self.get("item_name") or self.get("item_code"))

	def autoname(self):
		if self.meta.has_field('booking_number'):
			set_name_by_naming_series(self, 'booking_number')

	def validate(self):
		super(VehicleBookingOrder, self).validate()

		self.ensure_supplier_is_not_blocked()

		self.validate_allocation()
		self.validate_color()
		self.validate_vehicle_quotation()

		self.calculate_outstanding_amount()
		self.validate_payment_adjustment()

		self.set_title()
		self.get_terms_and_conditions()

		self.update_payment_status()
		self.update_delivery_status()
		self.update_invoice_status()
		self.update_transfer_customer()
		self.set_status()

	def before_submit(self):
		self.validate_delivery_period_mandatory()
		self.validate_color_mandatory()

	def on_submit(self):
		self.update_vehicle_quotation()
		self.update_allocation_status()
		self.update_vehicle_status()

	def on_cancel(self):
		self.update_vehicle_quotation()
		self.update_allocation_status()
		self.update_vehicle_status()
		self.db_set('status', 'Cancelled')

	def onload(self):
		super(VehicleBookingOrder, self).onload()

		if self.docstatus == 1:
			from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import set_can_change_onload
			set_can_change_onload(self)

	def before_print(self):
		super(VehicleBookingOrder, self).before_print()
		self.get_payment_details()

	def set_title(self):
		self.title = self.customer_name

	def get_payment_details(self):
		self.customer_payments = []
		self.supplier_payments = []

		if self.docstatus == 2:
			return

		payment_entries = get_booking_payments(self.name, include_draft=cint(self.docstatus == 0))
		self.customer_payments, self.supplier_payments = separate_customer_and_supplier_payments(payment_entries)

		self.is_full_payment = False
		self.is_partial_payment = False

		if self.customer_payments:
			initial_payments, balance_payments = separate_advance_and_balance_payments(self.customer_payments, self.supplier_payments)

			initial_payments_amount = flt(sum([d.amount for d in initial_payments]), self.precision('invoice_total'))
			self.is_full_payment = initial_payments_amount >= self.invoice_total
			self.is_partial_payment = not self.is_full_payment

	def validate_vehicle_item(self):
		super(VehicleBookingOrder, self).validate_vehicle_item()

		# remove previous item code if Draft or if current item code and previous item code are the same
		if self.docstatus == 0 or (self.docstatus == 1 and self.previous_item_code == self.item_code):
			self.previous_item_code = None
			self.previous_item_name = None

	def validate_vehicle(self):
		super(VehicleBookingOrder, self).validate_vehicle()

		if self.get('vehicle'):
			existing_filters = {"docstatus": 1, "vehicle": self.vehicle}
			if not self.is_new():
				existing_filters['name'] = ['!=', self.name]

			existing_booking = frappe.get_all("Vehicle Booking Order", filters=existing_filters, limit=1)
			existing_booking = existing_booking[0].name if existing_booking else None
			if existing_booking:
				frappe.throw(_("Cannot select Vehicle {0} because it is already ordered in {1}")
					.format(self.vehicle, existing_booking))

	def validate_allocation(self):
		if not self.vehicle_allocation_required:
			self.allocation_period = None
			self.vehicle_allocation = None

		if self.vehicle_allocation:
			allocation_doc = frappe.get_doc("Vehicle Allocation", self.vehicle_allocation)

			self.allocation_period = allocation_doc.allocation_period
			self.delivery_period = allocation_doc.delivery_period
			self.allocation_title = get_allocation_title(allocation_doc)

			if allocation_doc.docstatus != 1:
				frappe.throw(_("Vehicle Allocation {0} ({1}) is not submitted")
					.format(self.allocation_title, self.vehicle_allocation))

			if allocation_doc.item_code != self.item_code and (not self.previous_item_code or allocation_doc.item_code != self.previous_item_code):
				frappe.throw(_("Vehicle Allocation {0} ({1}) Vehicle Item {2} does not match Vehicle Booking Order Vehicle Item {3}")
					.format(self.allocation_title, self.vehicle_allocation,
						frappe.bold(allocation_doc.item_name or allocation_doc.item_code),
						frappe.bold(self.previous_item_code or self.item_code)))

			if allocation_doc.supplier != self.supplier:
				frappe.throw(_("Vehicle Allocation {0} ({1}) Supplier {2} does not match Vehicle Booking Order Supplier {3}")
					.format(self.allocation_title, self.vehicle_allocation,
						frappe.bold(allocation_doc.supplier_name or allocation_doc.supplier),
						frappe.bold(self.supplier_name or self.supplier)))

			if allocation_doc.vehicle_color:
				if self.color_1 != allocation_doc.vehicle_color:
					frappe.throw(_("Vehicle Allocation {0} ({1}) Vehicle Color {2} does not match Vehicle Booking Order Color (Priority 1) {3}")
						.format(self.allocation_title, self.vehicle_allocation,
							frappe.bold(allocation_doc.vehicle_color),
							frappe.bold(self.color_1)))

			existing_filters = {"docstatus": 1, "vehicle_allocation": self.vehicle_allocation}
			if not self.is_new():
				existing_filters['name'] = ['!=', self.name]

			existing_booking = frappe.get_all("Vehicle Booking Order", filters=existing_filters, limit=1)
			existing_booking = existing_booking[0].name if existing_booking else None
			if existing_booking:
				frappe.throw(_("Cannot select Vehicle Allocation {0} ({1}) because it is already ordered in {2}")
					.format(self.allocation_title, self.vehicle_allocation, existing_booking))

		else:
			self.allocation_title = ""

	def validate_color(self):
		# remove previous color if Draft or if current color and previous color are the same
		if self.docstatus == 0 or (self.docstatus == 1 and self.previous_color == self.color_1):
			self.previous_color = None

	def validate_vehicle_quotation(self):
		if self.vehicle_quotation:
			quotation_company = frappe.db.get_value("Vehicle Quotation", self.vehicle_quotation, 'company')
			if self.company != quotation_company:
				frappe.throw(_("Company in Vehicle Quotation {0} does not match with Vehicle Booking Order")
					.format(self.vehicle_quotation))

	def update_vehicle_quotation(self):
		if self.vehicle_quotation:
			doc = frappe.get_doc("Vehicle Quotation", self.vehicle_quotation)
			if doc.docstatus == 2:
				frappe.throw(_("Vehicle Quotation {0} is cancelled").format(self.vehicle_quotation))

			doc.set_status(update=True)
			doc.notify_update()
			doc.update_opportunity()

	def update_vehicle_status(self):
		if self.vehicle:
			is_booked = cint(self.docstatus == 1)
			update_vehicle_booked(self.vehicle, is_booked)

	def update_allocation_status(self):
		if self.vehicle_allocation:
			is_booked = cint(self.docstatus == 1)
			update_allocation_booked(self.vehicle_allocation, is_booked)

	def validate_color_mandatory(self):
		if not self.color_1:
			frappe.throw(_("Color (1st Priority) is mandatory before submission"))

	def calculate_outstanding_amount(self):
		if self.docstatus == 0:
			self.customer_advance = 0
			self.supplier_advance = 0
			self.payment_adjustment = 0

		self.payment_adjustment = flt(self.payment_adjustment, self.precision('payment_adjustment'))

		if self.status == "Cancelled Booking":
			self.customer_outstanding = 0
			self.supplier_outstanding = 0
		else:
			self.customer_outstanding = flt(self.invoice_total - self.customer_advance + self.payment_adjustment,
				self.precision('customer_outstanding'))
			self.supplier_outstanding = flt(self.invoice_total - self.supplier_advance + self.payment_adjustment,
				self.precision('supplier_outstanding'))

		self.validate_outstanding_amount()

	def validate_outstanding_amount(self):
		if self.customer_outstanding < 0:
			frappe.throw(_("Customer Advance Received cannot be greater than the Invoice Total"))
		if self.supplier_outstanding < 0:
			frappe.throw(_("Supplier Advance Paid cannot be greater than the Invoice Total"))

	def validate_payment_adjustment(self):
		maximum_payment_adjustment = frappe.get_cached_value("Vehicles Settings", None, "maximum_payment_adjustment")
		maximum_payment_adjustment = flt(maximum_payment_adjustment, self.precision('payment_adjustment'))
		if maximum_payment_adjustment:
			if abs(flt(self.payment_adjustment)) > maximum_payment_adjustment:
				frappe.throw(_("Payment Adjustment cannot be greater than {0}")
					.format(frappe.format(maximum_payment_adjustment, df=self.meta.get_field('payment_adjustment'))))

		if abs(flt(self.payment_adjustment)) > self.invoice_total:
			frappe.throw(_("Payment Adjustment cannot be greater than the Invoice Total"))

	def update_paid_amount(self, update=False):
		payments = dict(frappe.db.sql("""
			select payment_type, sum(total_amount)
			from `tabVehicle Booking Payment`
			where vehicle_booking_order = %s and docstatus = 1
			group by payment_type
		""", self.name))

		self.customer_advance = flt(payments.get('Receive'), self.precision('customer_advance'))
		self.supplier_advance = flt(payments.get('Pay'), self.precision('supplier_advance'))

		if update:
			self.db_set({
				'customer_advance': self.customer_advance,
				'supplier_advance': self.supplier_advance
			})

	def update_payment_status(self, update=False):
		self.calculate_outstanding_amount()

		if self.customer_outstanding > 0:
			if getdate(today()) > getdate(self.due_date):
				self.customer_payment_status = "Overdue"
			elif self.customer_advance == 0:
				self.customer_payment_status = "Unpaid"
			else:
				self.customer_payment_status = "Partially Paid"
		else:
			self.customer_payment_status = "Paid"

		if self.supplier_outstanding > 0:
			if getdate(today()) > getdate(self.due_date):
				self.supplier_payment_status = "Overdue"
			elif self.supplier_advance == 0:
				self.supplier_payment_status = "Unpaid"
			else:
				self.supplier_payment_status = "Partially Paid"
		else:
			self.supplier_payment_status = "Paid"

		if update:
			self.db_set({
				'customer_outstanding': self.customer_outstanding,
				'supplier_outstanding': self.supplier_outstanding,
				'customer_payment_status': self.customer_payment_status,
				'supplier_payment_status': self.supplier_payment_status,
			})

	def update_delivery_status(self, update=False):
		vehicle_receipt = None
		vehicle_delivery = None

		if self.docstatus != 0:
			vehicle_receipt = self.get_vehicle_receipts()

			vehicle_delivery = frappe.db.get_all("Vehicle Delivery", {"vehicle_booking_order": self.name, "docstatus": 1},
				['name', 'posting_date'])

			if len(vehicle_receipt) > 1:
				frappe.throw(_("Vehicle Receipt already exists against Vehicle Booking Order"))
			if len(vehicle_delivery) > 1:
				frappe.throw(_("Vehicle Delivery already exists against Vehicle Booking Order"))

		vehicle_receipt = vehicle_receipt[0] if vehicle_receipt else frappe._dict()
		vehicle_delivery = vehicle_delivery[0] if vehicle_delivery else frappe._dict()

		if vehicle_delivery:
			self.check_outstanding_payment_for_delivery()

		# open stock
		if vehicle_receipt and not vehicle_receipt.vehicle_booking_order:
			self.vehicle_receipt = vehicle_receipt.name
		else:
			self.vehicle_receipt = None

		self.vehicle_received_date = vehicle_receipt.posting_date
		self.vehicle_delivered_date = vehicle_delivery.posting_date
		self.lr_no = vehicle_receipt.lr_no

		if not vehicle_receipt:
			self.delivery_status = "To Receive"
		elif not vehicle_delivery:
			self.delivery_status = "To Deliver"
		else:
			self.delivery_status = "Delivered"

		if update:
			self.db_set({
				"vehicle_receipt": self.vehicle_receipt,
				"vehicle_received_date": self.vehicle_received_date,
				"vehicle_delivered_date": self.vehicle_delivered_date,
				"lr_no": self.lr_no,
				"delivery_status": self.delivery_status
			})

	def check_outstanding_payment_for_delivery(self):
		if flt(self.customer_outstanding):
			frappe.throw(_("Cannot deliver vehicle because there is a Customer Outstanding of {0}")
				.format(self.get_formatted("customer_outstanding")))
		if flt(self.supplier_outstanding):
			frappe.throw(_("Cannot deliver vehicle because there is a Supplier Outstanding of {0}")
				.format(self.get_formatted("supplier_outstanding")))

	def get_notification_count(self, notification_type, notification_medium):
		row = self.get('notification_count',
			{"notification_type": notification_type, "notification_medium": notification_medium})

		row = row[0] if row else {}
		return cint(row.get('notification_count'))

	def add_notification_count(self, notification_type, notification_medium, count=1, update=False):
		filters = {"notification_type": notification_type, "notification_medium": notification_medium}

		row = self.get('notification_count', filters)
		if row:
			row = row[0]
		else:
			row = self.append('notification_count', filters)
			row.notification_count = 0

		count = cint(count) or 1
		row.notification_count += count

		if update:
			row.db_update()

	def get_vehicle_receipts(self):
		fields = ['name', 'posting_date', 'lr_no', 'supplier', 'vehicle_booking_order']

		vehicle_receipts = frappe.db.get_all("Vehicle Receipt", {"vehicle_booking_order": self.name, "docstatus": 1}, fields)

		# open stock
		if not vehicle_receipts and self.vehicle:
			vehicle_receipts = frappe.db.get_all("Vehicle Receipt", {"vehicle": self.vehicle, "docstatus": 1}, fields,
				order_by='timestamp(posting_date, posting_time) asc', limit=1)

		return vehicle_receipts

	def update_invoice_status(self, update=False):
		vehicle_invoice_receipt = None
		vehicle_invoice_delivery = None

		if self.docstatus != 0:
			vehicle_invoice_receipt = frappe.db.get_all("Vehicle Invoice Receipt", {"vehicle_booking_order": self.name, "docstatus": 1},
				['name', 'posting_date', 'bill_no', 'bill_date'])
			vehicle_invoice_delivery = frappe.db.get_all("Vehicle Invoice Delivery", {"vehicle_booking_order": self.name, "docstatus": 1},
				['name', 'posting_date'])

			if len(vehicle_invoice_receipt) > 1:
				frappe.throw(_("Vehicle Invoice Receipt already exists against Vehicle Booking Order"))
			if len(vehicle_invoice_delivery) > 1:
				frappe.throw(_("Vehicle Invoice Delivery already exists against Vehicle Booking Order"))

			if vehicle_invoice_delivery and not vehicle_invoice_receipt:
				frappe.throw(_("Cannot make Vehicle Invoice Delivery against Vehicle Booking Order before making Vehicle Invoice Receipt"))

		vehicle_invoice_receipt = vehicle_invoice_receipt[0] if vehicle_invoice_receipt else frappe._dict()
		vehicle_invoice_delivery = vehicle_invoice_delivery[0] if vehicle_invoice_delivery else frappe._dict()

		if vehicle_invoice_receipt and (not vehicle_invoice_receipt.bill_no or not vehicle_invoice_receipt.bill_date):
			frappe.throw(_("Invoice No and Invoice Date is mandatory for Vehicle Invoice Receipt against Vehicle Booking Order"))

		self.invoice_received_date = vehicle_invoice_receipt.posting_date
		self.invoice_delivered_date = vehicle_invoice_delivery.posting_date
		self.bill_no = vehicle_invoice_receipt.bill_no
		self.bill_date = vehicle_invoice_receipt.bill_date

		if self.invoice_received_date and self.invoice_delivered_date:
			if getdate(self.invoice_delivered_date) < getdate(self.invoice_received_date):
				frappe.throw(_("Invoice Delivered Date cannot be before Invoice Received Date"))

		if not vehicle_invoice_receipt:
			self.invoice_status = "To Receive"
		elif not vehicle_invoice_delivery:
			self.invoice_status = "To Deliver"
		else:
			self.invoice_status = "Delivered"

		if update:
			self.db_set({
				"invoice_received_date": self.invoice_received_date,
				"invoice_delivered_date": self.invoice_delivered_date,
				"bill_no": self.bill_no,
				"bill_date": self.bill_date,
				"invoice_status": self.invoice_status
			})

	def update_transfer_customer(self, update=False):
		vehicle_transfer_letter = None

		if self.docstatus != 0:
			vehicle_transfer_letter = frappe.db.get_all("Vehicle Transfer Letter", {"vehicle_booking_order": self.name, "docstatus": 1},
				['customer', 'customer_name'], order_by="posting_date desc, creation desc", limit=1)

		vehicle_transfer_letter = vehicle_transfer_letter[0] if vehicle_transfer_letter else frappe._dict()

		self.transfer_customer = vehicle_transfer_letter.customer
		self.transfer_customer_name = vehicle_transfer_letter.customer_name

		if update:
			self.db_set({
				"transfer_customer": self.transfer_customer,
				"transfer_customer_name": self.transfer_customer_name
			})

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		previous_status = self.status

		if self.docstatus == 2:
			self.status = "Cancelled"

		elif self.docstatus == 1 and self.status == "Cancelled Booking":
			pass

		elif self.docstatus == 1:
			if self.customer_outstanding > 0 or self.supplier_outstanding > 0:
				if self.customer_advance > self.supplier_advance:
					if self.vehicle_allocation_required and not self.vehicle_allocation:
						self.status = "To Assign Allocation"
					else:
						self.status = "To Deposit Payment"
				else:
					if getdate(self.due_date) < getdate(today()):
						self.status = "Payment Overdue"
					else:
						self.status = "To Receive Payment"

			elif getdate(self.delivery_date) < getdate(today()) and self.delivery_status != "Delivered":
				self.status = "Delivery Overdue"

			elif self.vehicle_allocation_required and not self.vehicle_allocation:
				self.status = "To Assign Allocation"

			elif not self.vehicle:
				self.status = "To Assign Vehicle"

			elif self.delivery_status == "To Receive":
				self.status = "To Receive Vehicle"

			elif self.invoice_status == "To Receive":
				self.status = "To Receive Invoice"

			elif self.delivery_status == "To Deliver":
				self.status = "To Deliver Vehicle"

			elif self.invoice_status == "To Deliver":
				self.status = "To Deliver Invoice"

			else:
				self.status = "Completed"

		else:
			self.status = "Draft"

		self.add_status_comment(previous_status)

		if update:
			self.db_set('status', self.status, update_modified=update_modified)

	def check_cancelled(self, throw=False):
		if self.status == "Cancelled Booking" or self.docstatus == 2:
			if throw:
				frappe.throw(_("Vehicle Booking Order {0} is cancelled").format(self.name))

			return True

		return False


@frappe.whitelist()
def get_next_document(vehicle_booking_order, doctype):
	doc = frappe.get_doc("Vehicle Booking Order", vehicle_booking_order)

	if doc.docstatus != 1:
		frappe.throw(_("Vehicle Booking Order must be submitted"))

	doc.check_cancelled(throw=True)

	if doctype == "Vehicle Receipt":
		return get_vehicle_receipt(doc)
	elif doctype == "Vehicle Delivery":
		return get_vehicle_delivery(doc)
	elif doctype == "Vehicle Invoice Receipt":
		return get_vehicle_invoice_receipt(doc)
	elif doctype == "Vehicle Invoice Delivery":
		return get_vehicle_invoice_delivery(doc)
	elif doctype == "Vehicle Transfer Letter":
		return get_vehicle_transfer_letter(doc)
	else:
		frappe.throw(_("Invalid DocType"))


def get_vehicle_receipt(source):
	from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import can_receive_vehicle

	can_receive_vehicle(source, throw=True)
	check_if_doc_exists("Vehicle Receipt", source.name)

	target = frappe.new_doc("Vehicle Receipt")
	set_next_document_values(source, target)
	target.run_method("set_missing_values")
	return target


def get_vehicle_delivery(source):
	from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import can_deliver_vehicle

	can_deliver_vehicle(source, throw=True)
	source.check_outstanding_payment_for_delivery()
	check_if_doc_exists("Vehicle Delivery", source.name)

	target = frappe.new_doc("Vehicle Delivery")
	set_next_document_values(source, target)
	target.run_method("set_missing_values")
	return target


def get_vehicle_transfer_letter(source):
	from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import can_transfer_vehicle

	can_transfer_vehicle(source, throw=True)
	check_if_doc_exists("Vehicle Transfer Letter", source.name)

	if not has_previous_doc("Vehicle Delivery", source):
		frappe.throw(_("Cannot make Vehicle Transfer Letter against Vehicle Booking Order before making Vehicle Delivery"))

	target = frappe.new_doc("Vehicle Transfer Letter")
	set_next_document_values(source, target)
	target.run_method("set_missing_values")
	return target


def get_vehicle_invoice_receipt(source):
	from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import can_receive_invoice

	can_receive_invoice(source, throw=True)
	check_if_doc_exists("Vehicle Invoice Receipt", source.name)

	target = frappe.new_doc("Vehicle Invoice Receipt")
	set_next_document_values(source, target)
	target.run_method("set_missing_values")
	return target


def get_vehicle_invoice_delivery(source):
	from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import can_deliver_invoice

	can_deliver_invoice(source, throw=True)
	check_if_doc_exists("Vehicle Invoice Delivery", source.name)

	if not has_previous_doc("Vehicle Invoice Receipt", source):
		frappe.throw(_("Cannot make Vehicle Invoice Delivery against Vehicle Booking Order before making Vehicle Invoice Receipt"))

	target = frappe.new_doc("Vehicle Invoice Delivery")
	set_next_document_values(source, target)
	target.run_method("set_missing_values")
	return target


def check_if_doc_exists(doctype, vehicle_booking_order):
	existing = frappe.db.get_value(doctype, {"vehicle_booking_order": vehicle_booking_order, "docstatus": ["<", 2]})
	if existing:
		frappe.throw(_("{0} already exists").format(frappe.get_desk_link(doctype, existing)))


def has_previous_doc(doctype, source):
	prev_docname = frappe.db.get_value(doctype, {"vehicle_booking_order": source.name, "docstatus": 1})
	return prev_docname


def set_next_document_values(source, target):
	if not source.vehicle and target.doctype != 'Purchase Order':
		frappe.throw(_("Please set Vehicle first"))
	if source.vehicle_allocation_required and not source.vehicle_allocation and target.doctype != 'Purchase Order':
		frappe.throw(_("Please set Vehicle Allocation first"))

	target.vehicle_booking_order = source.name
	target.company = source.company

	if target.doctype != "Vehicle Transfer Letter":
		if target.meta.has_field('customer'):
			target.customer = source.customer
			target.customer_name = source.customer_name

		if target.meta.has_field('customer_address'):
			target.customer_address = source.customer_address

		if target.meta.has_field('contact_person'):
			target.contact_person = source.contact_person

	if target.meta.has_field('supplier'):
		target.supplier = source.supplier

	if target.meta.has_field('warehouse'):
		target.warehouse = source.warehouse

	target.item_code = source.item_code
	target.vehicle = source.vehicle


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


@frappe.whitelist()
def send_sms(receiver_list, msg, success_msg=True, type=None,
		reference_doctype=None, reference_name=None, party_doctype=None, party_name=None):
	from frappe.core.doctype.sms_settings.sms_settings import send_sms

	if not type:
		frappe.throw(_("SMS Type is mandatory"))

	if reference_doctype != 'Vehicle Booking Order':
		frappe.throw(_("Reference DocType must be Vehicle Booking Order"))

	vbo_doc = frappe.get_doc("Vehicle Booking Order", reference_name)

	if type != "Booking Cancellation" and vbo_doc.check_cancelled():
		frappe.throw(_("Cannot send {0} SMS because Vehicle Booking Order is cancelled").format(type))
	if type == "Booking Confirmation" and vbo_doc.delivery_status != "To Receive":
		frappe.throw(_("Cannot send Booking Confirmation SMS after receiving Vehicle"))
	if type == "Balance Payment Request" and not vbo_doc.customer_outstanding:
		frappe.throw(_("Cannot send Balance Payment Request SMS because Customer Outstanding amount is zero"))
	if type == "Ready For Delivery" and vbo_doc.delivery_status != 'To Deliver':
		frappe.throw(_("Cannot send Ready For Delivery SMS because delivery status is not 'To Deliver'"))
	if type == "Congratulations" and vbo_doc.invoice_status != 'Delivered':
		frappe.throw(_("Cannot send Congratulations SMS because Invoice has not been delivered yet"))

	vbo_doc.add_notification_count(type, "SMS", update=1)
	vbo_doc.notify_update()

	send_sms(receiver_list, msg, success_msg, type, reference_doctype, reference_name, party_doctype, party_name)


def update_overdue_status():
	if 'Vehicles' not in frappe.get_active_domains():
		return

	frappe.db.sql("""
		update `tabVehicle Booking Order`
		set customer_payment_status = 'Overdue'
		where docstatus = 1 and due_date < CURDATE() and customer_outstanding > 0 and status != 'Cancelled Booking'
	""")
	frappe.db.sql("""
		update `tabVehicle Booking Order`
		set supplier_payment_status = 'Overdue'
		where docstatus = 1 and due_date < CURDATE() and supplier_outstanding > 0 and status != 'Cancelled Booking'
	""")

	frappe.db.sql("""
		update `tabVehicle Booking Order`
		set status = 'Payment Overdue'
		where docstatus = 1
			and status = 'To Receive Payment'
			and due_date < CURDATE()
			and customer_outstanding > 0
	""")

	frappe.db.sql("""
		update `tabVehicle Booking Order`
		set status = 'Delivery Overdue'
		where docstatus = 1
			and delivery_status != 'Delivered'
			and delivery_date < CURDATE()
			and customer_outstanding <= 0
			and supplier_outstanding <= 0
			and status != 'Cancelled Booking'
	""")


def update_vehicle_booked(vehicle, is_booked):
	is_booked = cint(is_booked)
	frappe.db.set_value("Vehicle", vehicle, "is_booked", is_booked, notify=True)


def update_allocation_booked(vehicle_allocation, is_booked):
	is_booked = cint(is_booked)
	frappe.db.set_value("Vehicle Allocation", vehicle_allocation, "is_booked", is_booked, notify=True)
