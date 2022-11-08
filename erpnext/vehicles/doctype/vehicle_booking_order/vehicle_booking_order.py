# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.vehicles.utils import get_booking_payments, separate_customer_and_supplier_payments, separate_advance_and_balance_payments
from frappe import _
from frappe.utils import cint, flt, getdate, today, combine_datetime, now_datetime
from frappe.model.naming import set_name_by_naming_series
from erpnext.vehicles.doctype.vehicle_allocation.vehicle_allocation import get_allocation_title
from erpnext.vehicles.vehicle_booking_controller import VehicleBookingController
from frappe.core.doctype.sms_settings.sms_settings import enqueue_template_sms


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

		self.set_payment_status()
		self.set_delivery_status()
		self.set_invoice_status()
		self.set_registration_status()
		self.set_pdi_status()
		self.set_transfer_customer()
		self.set_status()

	def before_submit(self):
		self.validate_delivery_period_mandatory()
		self.validate_color_mandatory()

	def on_submit(self):
		self.update_vehicle_quotation()
		self.update_opportunity()
		self.update_allocation_status()
		self.update_vehicle_status()

	def on_cancel(self):
		self.update_vehicle_quotation()
		self.update_opportunity()
		self.update_allocation_status()
		self.update_vehicle_status()
		self.db_set('status', 'Cancelled')

	def onload(self):
		super(VehicleBookingOrder, self).onload()

		if self.docstatus == 1:
			from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import set_can_change_onload
			set_can_change_onload(self)
			self.set_can_notify_onload()
			self.set_vehicle_warehouse_onload()

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

			if cint(allocation_doc.is_expired):
				frappe.throw(_("Vehicle Allocation {0} ({1}) is expired")
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
		if self.get('vehicle_quotation'):
			doc = frappe.get_doc("Vehicle Quotation", self.vehicle_quotation)
			if doc.docstatus == 2:
				frappe.throw(_("Vehicle Quotation {0} is cancelled").format(self.vehicle_quotation))

			doc.set_status(update=True)
			doc.notify_update()

	def update_opportunity(self):
		if self.get('opportunity'):
			doc = frappe.get_doc("Opportunity", self.opportunity)
			doc.set_status(update=True)
			doc.notify_update()

	def update_vehicle_status(self):
		if self.vehicle:
			is_booked = cint(self.docstatus == 1)
			update_vehicle_booked(self.vehicle, is_booked)

	def update_allocation_status(self):
		if self.vehicle_allocation:
			is_booked = cint(self.docstatus == 1)
			is_cancelled = cint(self.status == "Cancelled Booking")
			update_allocation_booked(self.vehicle_allocation, is_booked, is_cancelled)

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

	def set_payment_status(self, update=False):
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

	def set_delivery_status(self, update=False):
		vehicle_receipts = None
		vehicle_deliveries = None

		if self.docstatus != 0:
			vehicle_receipts = self.get_vehicle_receipts()
			vehicle_deliveries = frappe.db.get_all("Vehicle Delivery", {"vehicle_booking_order": self.name, "docstatus": 1},
				['name', 'posting_date', 'is_return'], order_by="posting_date, posting_time, creation")

		vehicle_receipt = frappe._dict()
		vehicle_delivery = frappe._dict()

		if vehicle_receipts and not vehicle_receipts[-1].get('is_return'):
			vehicle_receipt = vehicle_receipts[-1]

		if vehicle_deliveries and not vehicle_deliveries[-1].get('is_return'):
			vehicle_delivery = vehicle_deliveries[-1]

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

		if vehicle_delivery:
			self.delivery_status = "Delivered"
		elif vehicle_receipt:
			self.delivery_status = "In Stock"
		elif self.outstation_delivery:
			self.delivery_status = "Not Applicable"
		else:
			self.delivery_status = "Not Received"

		if self.delivery_status in ["Not Received", "In Stock"] and getdate(self.delivery_date) < getdate(today()):
			self.delivery_overdue = 1
		else:
			self.delivery_overdue = 0

		if update:
			self.db_set({
				"vehicle_receipt": self.vehicle_receipt,
				"vehicle_received_date": self.vehicle_received_date,
				"vehicle_delivered_date": self.vehicle_delivered_date,
				"lr_no": self.lr_no,
				"delivery_status": self.delivery_status,
				"delivery_overdue": self.delivery_overdue
			})

	def get_vehicle_receipts(self):
		fields = ['name', 'posting_date', 'is_return', 'lr_no', 'supplier', 'vehicle_booking_order']

		vehicle_receipts = frappe.db.get_all("Vehicle Receipt", {"vehicle_booking_order": self.name, "docstatus": 1}, fields,
			order_by='posting_date, posting_time, creation')

		# open stock
		if not vehicle_receipts and self.vehicle:
			vehicle_receipts = frappe.db.get_all("Vehicle Receipt", {"vehicle": self.vehicle, "docstatus": 1}, fields,
				order_by='posting_date, posting_time, creation')

		return vehicle_receipts

	def check_outstanding_payment_for_delivery(self):
		if flt(self.customer_outstanding):
			frappe.throw(_("Cannot deliver vehicle because there is a Customer Outstanding of {0}")
				.format(self.get_formatted("customer_outstanding")))
		if flt(self.supplier_outstanding):
			frappe.throw(_("Cannot deliver vehicle because there is a Supplier Outstanding of {0}")
				.format(self.get_formatted("supplier_outstanding")))

	def set_invoice_status(self, update=False):
		vehicle_invoice = None

		if self.vehicle:
			vehicle_invoice = frappe.db.get_all("Vehicle Invoice", {"vehicle": self.vehicle, "docstatus": 1},
				['name', 'posting_date', 'bill_no', 'bill_date', 'delivered_date', 'status', 'issued_for'],
				order_by="posting_date desc, creation desc")

		vehicle_invoice = vehicle_invoice[0] if vehicle_invoice else frappe._dict()

		if vehicle_invoice and (not vehicle_invoice.bill_no or not vehicle_invoice.bill_date):
			frappe.throw(_("Invoice No and Invoice Date is mandatory for Vehicle Invoice against Vehicle Booking Order"))

		self.invoice_received_date = vehicle_invoice.posting_date
		self.invoice_delivered_date = vehicle_invoice.delivered_date
		self.bill_no = vehicle_invoice.bill_no
		self.bill_date = vehicle_invoice.bill_date

		if self.invoice_received_date and self.invoice_delivered_date:
			if getdate(self.invoice_delivered_date) < getdate(self.invoice_received_date):
				frappe.throw(_("Invoice Delivered Date cannot be before Invoice Received Date"))

		if vehicle_invoice:
			self.invoice_status = vehicle_invoice.status
			self.invoice_issued_for = vehicle_invoice.issued_for if vehicle_invoice.status == "Issued" else None
		else:
			self.invoice_status = "Not Received"
			self.invoice_issued_for = None

		if update:
			self.db_set({
				"invoice_received_date": self.invoice_received_date,
				"invoice_delivered_date": self.invoice_delivered_date,
				"bill_no": self.bill_no,
				"bill_date": self.bill_date,
				"invoice_status": self.invoice_status,
				"invoice_issued_for": self.invoice_issued_for,
			})

	def set_registration_status(self, update=False):
		from erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order import get_vehicle_registration_order
		from erpnext.vehicles.doctype.vehicle_registration_receipt.vehicle_registration_receipt import get_vehicle_registration_receipt

		vehicle_registration_receipt = get_vehicle_registration_receipt(self.vehicle)
		vehicle_registration_order = get_vehicle_registration_order(self.vehicle, self.name)

		if vehicle_registration_receipt:
			self.registration_status = 'Registered'
		elif vehicle_registration_order:
			if self.invoice_status == 'Issued' and self.invoice_issued_for == 'Registration':
				self.registration_status = 'In Process'
			else:
				self.registration_status = 'Ordered'
		else:
			self.registration_status = 'Not Ordered'

		if update:
			self.db_set({
				'registration_status': self.registration_status
			})

	def set_pdi_status(self, update=False):
		previous_pdi_status = self.pdi_status

		project = frappe.get_all("Project", fields=['name', 'status', 'ready_to_close'], filters={
			'vehicle_booking_order': self.name,
			'status': ['!=', 'Cancelled'],
			'vehicle_received_date': ['is', 'set']
		}, limit=1)
		project = project[0] if project else None

		if project:
			if project.ready_to_close or project.status in ['Completed', 'Closed']:
				self.pdi_status = "Done"
			else:
				self.pdi_status = "In Process"
		else:
			if cint(self.pdi_requested):
				self.pdi_status = "Requested"
			else:
				self.pdi_status = "Not Requested"

		if update and self.pdi_status != previous_pdi_status:
			self.db_set({
				'pdi_status': self.pdi_status
			})

	def set_transfer_customer(self, update=False):
		vehicle_transfer_letter = []
		vehicle_registration_receipt = []

		if self.docstatus != 0:
			vehicle_transfer_letter = frappe.db.get_all("Vehicle Transfer Letter", {"vehicle_booking_order": self.name, "docstatus": 1},
				['customer', 'customer_name', 'financer', 'financer_name', 'lessee_name', 'posting_date', 'creation'],
				order_by="posting_date desc, creation desc", limit=1)
			vehicle_registration_receipt = frappe.db.get_all("Vehicle Registration Receipt", {"vehicle_booking_order": self.name, "docstatus": 1},
				['customer', 'customer_name', 'financer', 'financer_name', 'lessee_name', 'posting_date', 'creation'],
				order_by="posting_date desc, creation desc", limit=1)

		transfer_transactions = vehicle_transfer_letter + vehicle_registration_receipt
		transfer_details = max(transfer_transactions, key=lambda d: (d.posting_date, d.creation)) if transfer_transactions else None

		if transfer_details and transfer_details.customer not in [self.customer, self.financer]:
			self.transfer_customer = transfer_details.customer
			self.transfer_customer_name = transfer_details.customer_name
			self.transfer_financer = transfer_details.financer
			self.transfer_financer_name = transfer_details.financer_name
			self.transfer_lessee_name = transfer_details.lessee_name
		else:
			self.transfer_customer = None
			self.transfer_customer_name = None
			self.transfer_financer = None
			self.transfer_financer_name = None
			self.transfer_lessee_name = None

		if update:
			self.db_set({
				"transfer_customer": self.transfer_customer,
				"transfer_customer_name": self.transfer_customer_name,
				"transfer_financer": self.transfer_financer,
				"transfer_financer_name": self.transfer_financer_name,
				"transfer_lessee_name": self.transfer_lessee_name,
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

			elif self.vehicle_allocation_required and not self.vehicle_allocation:
				self.status = "To Assign Allocation"

			elif self.delivery_status == "Not Received":
				self.status = "To Receive Vehicle"

			elif self.invoice_status == "Not Received":
				self.status = "To Receive Invoice"

			elif self.delivery_status == "In Stock":
				self.status = "To Deliver Vehicle"

			elif self.invoice_status != "Delivered":
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

	def set_vehicle_warehouse_onload(self):
		if self.delivery_status == "In Stock" and self.vehicle:
			vehicle_warehouse = frappe.db.get_value("Vehicle", self.vehicle, 'warehouse')
			vehicle_warehouse_name = frappe.db.get_value("Warehouse", vehicle_warehouse, 'warehouse_name')\
				if vehicle_warehouse else None

			self.set_onload('vehicle_warehouse', vehicle_warehouse)
			self.set_onload('vehicle_warehouse_name', vehicle_warehouse_name)

	def get_sms_args(self, notification_type=None):
		return frappe._dict({
			'receiver_list': [self.contact_mobile],
			'party_doctype': 'Customer',
			'party': self.customer
		})

	def set_can_notify_onload(self):
		notification_types = [
			'Booking Confirmation',
			'Balance Payment Due',
			'Balance Payment Confirmation',
			'Ready For Delivery',
			'Congratulations',
			'Booking Cancellation'
		]

		can_notify = frappe._dict()
		for notification_type in notification_types:
			can_notify[notification_type] = self.validate_notification(notification_type, throw=False)

		self.set_onload('can_notify', can_notify)

	def validate_notification(self, notification_type=None, throw=False):
		if not notification_type:
			if throw:
				frappe.throw(_("Notification Type is mandatory"))
			return False

		if self.docstatus != 1:
			if throw:
				frappe.throw(_("Cannot send notification because Vehicle Booking Order is not submitted"))
			return False

		# Not allowed if cancelled except for Booking Cancellation message
		if notification_type == "Booking Cancellation":
			if not self.check_cancelled():
				if throw:
					frappe.throw(_("Cannot send Booking Cancellation notification because Booking is not cancelled"))
				return False
		else:
			if self.check_cancelled():
				if throw:
					frappe.throw(_("Cannot send {0} notification because Vehicle Booking Order is cancelled").format(notification_type))
				return False

		if notification_type == "Booking Confirmation":
			if self.delivery_status in ["In Stock", "Delivered"]:
				if throw:
					frappe.throw(_("Cannot send Booking Confirmation notification after receiving Vehicle"))
				return False

		if notification_type == "Balance Payment Confirmation":
			if self.customer_advance <= 0:
				if throw:
					frappe.throw(_("Cannot send Balance Payment Confirmation notification because Customer Advance amount is 0"))
				return False

		if notification_type == "Balance Payment Due":
			if self.customer_outstanding <= 0:
				if throw:
					frappe.throw(_("Cannot send Balance Payment Due notification because Customer Outstanding amount is zero"))
				return False

			if not self.due_date or getdate() < getdate(self.due_date):
				if throw:
					frappe.throw(_("Cannot send Balance Payment Due notification because Due Date has not passed"))
				return False

		if notification_type == "Ready For Delivery":
			if self.delivery_status != 'In Stock':
				if throw:
					frappe.throw(_("Cannot send Ready For Delivery notification because Vehicle is not 'In Stock'"))
				return False

		if notification_type == "Congratulations":
			if self.delivery_status != 'Delivered':
				if throw:
					frappe.throw(_("Cannot send Congratulations notification because Vehicle has not been delivered yet"))
				return False

		return True

	def send_notification_on_payment(self, payment):
		if payment.payment_type != "Receive":
			return

		linked_payment_receipts = frappe.get_all("Vehicle Booking Payment",
			{"docstatus": 1, "payment_type": "Receive", "vehicle_booking_order": self.name})
		linked_payment_receipts = [d.name for d in linked_payment_receipts]

		if payment.name not in linked_payment_receipts:
			return

		context = {'payment': payment}

		if len(linked_payment_receipts) == 1:
			enqueue_template_sms(self, notification_type="Booking Confirmation", context=context)
		elif len(linked_payment_receipts) > 1:
			enqueue_template_sms(self, notification_type="Balance Payment Confirmation", context=context,
				allow_if_already_sent=True)

	def send_notification_on_delivery(self, vehicle_delivery):
		context = {'vehicle_delivery': vehicle_delivery}

		if vehicle_delivery.get('is_return'):
			return

		enqueue_template_sms(self, notification_type="Congratulations", context=context)

	def send_notification_on_payment_due(self):
		enqueue_template_sms(self, notification_type="Balance Payment Due")

	def send_notification_on_cancellation(self):
		enqueue_template_sms(self, notification_type="Booking Cancellation")


@frappe.whitelist()
def get_next_document(vehicle_booking_order, doctype):
	doc = frappe.get_doc("Vehicle Booking Order", vehicle_booking_order)

	if doc.docstatus != 1:
		frappe.throw(_("Vehicle Booking Order must be submitted"))

	doc.check_cancelled(throw=True)

	if doctype == "Vehicle Receipt":
		return get_vehicle_receipt(doc)
	elif doctype == "Vehicle Receipt Return":
		return get_vehicle_receipt_return(doc)
	elif doctype == "Vehicle Delivery":
		return get_vehicle_delivery(doc)
	elif doctype == "Vehicle Delivery Return":
		return get_vehicle_delivery_return(doc)
	elif doctype == "Vehicle Invoice":
		return get_vehicle_invoice(doc)
	elif doctype == "Vehicle Invoice Delivery":
		return get_vehicle_invoice_delivery(doc)
	elif doctype == "Vehicle Transfer Letter":
		return get_vehicle_transfer_letter(doc)
	elif doctype == "Vehicle Registration Order":
		return get_vehicle_registration_order(doc)
	elif doctype == "Project":
		return get_pdi_repair_order(doc)
	else:
		frappe.throw(_("Invalid DocType"))


def get_vehicle_receipt(source):
	from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import can_receive_vehicle

	can_receive_vehicle(source, throw=True)
	check_if_doc_exists("Vehicle Receipt", source.name, {'docstatus': 0, 'is_return': 0})

	target = frappe.new_doc("Vehicle Receipt")
	set_next_document_values(source, target)
	target.run_method("set_missing_values")
	return target


def get_vehicle_receipt_return(source):
	from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import can_receive_vehicle

	can_receive_vehicle(source, throw=True)
	check_if_doc_exists("Vehicle Receipt", source.name, {'docstatus': 0, 'is_return': 1})

	target = frappe.new_doc("Vehicle Receipt")
	target.is_return = 1
	set_next_document_values(source, target)
	target.run_method("set_missing_values")
	return target


def get_vehicle_delivery(source):
	from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import can_deliver_vehicle

	can_deliver_vehicle(source, throw=True)
	source.check_outstanding_payment_for_delivery()
	check_if_doc_exists("Vehicle Delivery", source.name, {'docstatus': 0, 'is_return': 0})

	target = frappe.new_doc("Vehicle Delivery")
	set_next_document_values(source, target)
	target.run_method("set_missing_values")
	return target


def get_vehicle_delivery_return(source):
	from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import can_deliver_vehicle

	can_deliver_vehicle(source, throw=True)
	check_if_doc_exists("Vehicle Delivery", source.name, {'docstatus': 0, 'is_return': 1})

	target = frappe.new_doc("Vehicle Delivery")
	target.is_return = 1
	set_next_document_values(source, target)
	target.run_method("set_missing_values")
	return target


def get_vehicle_transfer_letter(source):
	from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import can_transfer_vehicle

	can_transfer_vehicle(source, throw=True)
	check_if_doc_exists("Vehicle Transfer Letter", source.name)

	target = frappe.new_doc("Vehicle Transfer Letter")
	set_next_document_values(source, target)
	target.run_method("set_missing_values")
	return target


def get_vehicle_registration_order(source):
	check_if_doc_exists("Vehicle Registration Order", source.name)
	target = frappe.new_doc("Vehicle Registration Order")
	set_next_document_values(source, target)

	for d in source.sales_team:
		target.append('sales_team', {
			'sales_person': d.sales_person,
			'allocated_percentage': d.allocated_percentage,
		})

	target.run_method("set_missing_values")
	target.run_method("calculate_totals")
	return target


def get_vehicle_invoice(source):
	from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import can_receive_invoice

	can_receive_invoice(source, throw=True)
	check_if_doc_exists("Vehicle Invoice", source.name)

	target = frappe.new_doc("Vehicle Invoice")
	set_next_document_values(source, target)
	target.run_method("set_missing_values")
	return target


def get_vehicle_invoice_delivery(source):
	from erpnext.vehicles.doctype.vehicle_booking_order.change_booking import can_deliver_invoice

	can_deliver_invoice(source, throw=True)
	check_if_doc_exists("Vehicle Invoice Delivery", source.name, {'is_copy': 0})

	if not has_previous_doc("Vehicle Invoice", source):
		frappe.throw(_("Cannot deliver Vehicle Invoice against Vehicle Booking Order before receiving Vehicle Invoice"))

	target = frappe.new_doc("Vehicle Invoice Delivery")
	set_next_document_values(source, target)
	target.run_method("set_missing_values")
	return target


def get_pdi_repair_order(source):
	from erpnext.projects.doctype.project_type.project_type import get_project_type_defaults
	from erpnext.projects.doctype.project_workshop.project_workshop import get_project_workshop_details
	from erpnext.projects.doctype.project_template.project_template import guess_project_template

	if not frappe.has_permission("Project", "create"):
		frappe.throw(_("You do not have permission to make Repair Order"))

	check_if_doc_exists("Project", source.name, {'status': ['!=', 'Cancelled']})

	if not source.vehicle:
		frappe.throw(_("Please set Vehicle first"))

	target = frappe.new_doc("Project")

	target.company = source.company
	target.vehicle_booking_order = source.name
	target.customer = source.customer
	target.contact_person = source.contact_person
	target.applies_to_item = source.item_code
	target.applies_to_vehicle = source.vehicle
	target.project_name = _("PDI")

	vehicles_settings = frappe.get_cached_doc("Vehicles Settings", None)

	# Project Type
	target.project_type = vehicles_settings.pdi_project_type
	if target.project_type:
		target.update(get_project_type_defaults(target.project_type))

	# Project Workshop
	target.project_workshop = vehicles_settings.pdi_vehicle_workshop
	if target.project_workshop:
		target.update(get_project_workshop_details(target.project_workshop))

	# Project Template
	if target.applies_to_item and vehicles_settings.pdi_project_template_category:
		project_template = guess_project_template(vehicles_settings.pdi_project_template_category, target.applies_to_item)
		if project_template:
			target.append('project_templates', {'project_template': project_template})

	# Odometer
	if target.applies_to_vehicle:
		target.vehicle_first_odometer = cint(frappe.db.get_value("Vehicle", target.applies_to_vehicle, 'last_odometer'))

	target.run_method("set_missing_values")
	return target


def check_if_doc_exists(doctype, vehicle_booking_order, filters=None):
	filter_args = filters or {}
	filters = {"vehicle_booking_order": vehicle_booking_order, "docstatus": ["<", 2]}
	filters.update(filter_args)

	existing = frappe.db.get_value(doctype, filters)
	if existing:
		frappe.throw(_("{0} already exists").format(frappe.get_desk_link(doctype, existing)))


def has_previous_doc(doctype, source):
	prev_docname = frappe.db.get_value(doctype, {"vehicle_booking_order": source.name, "docstatus": 1})
	return prev_docname


def set_next_document_values(source, target):
	if not source.vehicle and target.doctype != 'Vehicle Registration Order':
		frappe.throw(_("Please set Vehicle first"))
	if source.vehicle_allocation_required and not source.vehicle_allocation and target.doctype != 'Purchase Order':
		frappe.throw(_("Please set Vehicle Allocation first"))

	target.company = source.company
	target.vehicle_booking_order = source.name
	target.item_code = source.item_code
	target.vehicle = source.vehicle

	if target.meta.has_field('registration_customer'):
		target.registration_customer = source.customer
		target.registration_customer_name = source.customer_name

	if target.meta.has_field('supplier'):
		target.supplier = source.supplier

	if target.meta.has_field('warehouse') and target.doctype not in ['Vehicle Delivery', 'Vehicle Movement']:
		target.warehouse = source.warehouse

	if target.meta.has_field('territory'):
		target.territory = source.territory


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
			and status != 'Cancelled Booking'
	""")

	frappe.db.sql("""
		update `tabVehicle Booking Order`
		set delivery_overdue = 1
		where docstatus = 1
			and delivery_status in ('Not Received', 'In Stock')
			and delivery_date < CURDATE()
			and customer_outstanding <= 0
			and status != 'Cancelled Booking'
	""")


def send_payment_overdue_notifications():
	from frappe.core.doctype.sms_settings.sms_settings import is_automated_sms_enabled
	from frappe.core.doctype.sms_template.sms_template import has_automated_sms_template

	if 'Vehicles' not in frappe.get_active_domains():
		return
	if not is_automated_sms_enabled():
		return
	if not has_automated_sms_template("Vehicle Booking Order", "Balance Payment Due"):
		return

	today_date = getdate(today())

	payment_due_notification_time = frappe.get_cached_value("Vehicles Settings", None, "payment_due_notification_time")
	if payment_due_notification_time:
		run_after = combine_datetime(today_date, payment_due_notification_time)
		if now_datetime() < run_after:
			return

	overdue_bookings_to_notify = frappe.db.sql_list("""
		select vbo.name
		from `tabVehicle Booking Order` vbo
		left join `tabNotification Count` n on n.parenttype = 'Vehicle Booking Order' and n.parent = vbo.name
			and n.notification_type = 'Balance Payment Due' and n.notification_medium = 'SMS'
		where vbo.docstatus = 1
			and vbo.status != 'Cancelled Booking'
			and vbo.customer_outstanding > 0
			and vbo.due_date = %s
			and vbo.due_date > vbo.transaction_date
			and n.last_scheduled_dt is null
			and n.last_sent_dt is null
	""", today_date)

	for name in overdue_bookings_to_notify:
		doc = frappe.get_doc("Vehicle Booking Order", name)
		doc.send_notification_on_payment_due()


def update_vehicle_booked(vehicle, is_booked):
	is_booked = cint(is_booked)
	frappe.db.set_value("Vehicle", vehicle, "is_booked", is_booked, notify=True)


def update_allocation_booked(vehicle_allocation, is_booked, is_cancelled):
	is_booked = cint(is_booked)
	is_cancelled = cint(is_cancelled)
	frappe.db.set_value("Vehicle Allocation", vehicle_allocation, {"is_booked": is_booked, "is_cancelled": is_cancelled},
		notify=True)
