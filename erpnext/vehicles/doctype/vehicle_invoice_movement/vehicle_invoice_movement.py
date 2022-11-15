# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController
from erpnext.vehicles.doctype.vehicle_invoice.vehicle_invoice import get_vehicle_invoice_details,\
	get_vehicle_invoice
from erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order import get_vehicle_registration_order


class VehicleInvoiceMovement(VehicleTransactionController):
	def get_feed(self):
		return _("{0} | {1}").format(self.purpose,
			self.get('supplier_name') or self.get('agent_name') or self.get('employee_name'))

	def validate(self):
		super(VehicleInvoiceMovement, self).validate()
		self.validate_duplicate_vehicle()
		self.validate_invoice_already_delivered()
		self.set_vehicle_invoice_details()
		self.validate_vehicle_invoice()
		self.validate_purpose()
		self.validate_party_name()
		self.set_vehicle_registration_order()
		self.validate_vehicle_registration_order()
		self.set_title()

	def before_submit(self):
		self.validate_invoice_not_received()

	def on_submit(self):
		self.update_vehicle_invoice()
		self.update_vehicle_booking_order_invoice()
		self.update_vehicle_booking_order_registration()
		self.update_vehicle_registration_order()

	def on_cancel(self):
		self.update_vehicle_invoice()
		self.update_vehicle_booking_order_invoice()
		self.update_vehicle_registration_order()

	def set_title(self):
		if self.purpose == "Receive":
			self.title = _("Receive From {0}").format(self.supplier_name or self.supplier)
		elif self.purpose == "Transfer":
			self.title = _("Transfer To {0}").format(self.employee_name or self.employee)
		elif self.purpose == "Issue":
			self.title = _("{0} Issue{1}").format(self.issued_for,
				" To {0}".format(self.agent_name or self.agent) if self.agent else "")
		elif self.purpose == "Return":
			self.title = _("{0} Return{1}").format(self.issued_for,
				" From {0}".format(self.agent_name or self.agent) if self.agent else "")
		else:
			self.title = _(self.purpose)

	def set_missing_values(self, doc=None, for_validate=False):
		for d in self.invoices:
			self.set_vehicle_booking_order_details(d, for_validate=for_validate)
			self.set_vehicle_details(d, for_validate=for_validate)
			self.set_item_details(d, for_validate=for_validate)

		self.set_customer_details(for_validate=for_validate)

	def validate_duplicate_vehicle(self):
		vehicles = set()
		for d in self.invoices:
			if d.vehicle:
				if d.vehicle in vehicles:
					frappe.throw(_("Row #{0}: Vehicle {1} is duplicate").format(d.idx, d.vehicle))
				vehicles.add(d.vehicle)

	def validate_invoice_already_delivered(self):
		for d in self.invoices:
			invoice_delivery = frappe.db.get_value("Vehicle Invoice Delivery", filters={
				"vehicle": d.vehicle,
				"docstatus": 1,
				"is_copy": 0,
				"posting_date": ['<=', getdate(self.posting_date)]
			})

			if invoice_delivery:
				frappe.throw(_("Row #{0}: Invoice for {1} has already been delivered in {2}")
					.format(d.idx, frappe.get_desk_link("Vehicle", d.vehicle),
						frappe.get_desk_link("Vehicle Invoice Delivery", invoice_delivery)))

	def set_vehicle_invoice_details(self):
		for d in self.invoices:
			d.vehicle_invoice = get_vehicle_invoice(d.vehicle)

			if self.purpose != 'Receive':
				d.update(get_vehicle_invoice_details(d.vehicle_invoice))

	def validate_vehicle_invoice(self):
		for d in self.invoices:
			if self.purpose == "Receive":
				if d.vehicle_invoice:
					frappe.throw(_("Row #{0}: Invoice for {1} has already been received in {2}")
						.format(d.idx, frappe.get_desk_link("Vehicle", d.vehicle),
							frappe.get_desk_link("Vehicle Invoice", d.vehicle_invoice)))
			else:
				if d.vehicle_invoice:
					received_date = frappe.db.get_value("Vehicle Invoice", d.vehicle_invoice, 'posting_date')
					if getdate(self.posting_date) < getdate(received_date):
						frappe.throw(_("Row {0}: Date cannot be before Invoice Received Date {1}")
							.format(d.idx, frappe.bold(frappe.format(getdate(received_date)))))

	def validate_purpose(self):
		if self.purpose == "Transfer":
			if not self.employee:
				frappe.throw(_("Employee is mandatory for transferring possession"))

		elif self.purpose in ['Issue', 'Return']:
			if not self.issued_for:
				frappe.throw(_("Issued For is mandatory for issuance and returns"))

		elif self.purpose == "Receive":
			if not self.supplier:
				frappe.throw(_("Supplier is mandatory for receiving invoice"))

		if self.purpose != "Receive":
			self.supplier = None

		if self.purpose not in ['Transfer', 'Return', 'Receive']:
			self.employee = None

		if self.purpose not in ['Issue', 'Return']:
			self.agent = None
			self.issued_for = None

	def validate_party_name(self):
		if not self.supplier:
			self.supplier_name = None
		if not self.employee:
			self.employee_name = None
		if not self.agent:
			self.agent_name = None

	def validate_invoice_not_received(self):
		if self.purpose == "Receive":
			return

		for d in self.invoices:
			if d.vehicle and not d.vehicle_invoice:
				frappe.throw(_("Row {0}: Invoice for {1} has not yet been received")
					.format(d.idx, frappe.get_desk_link('Vehicle', d.vehicle)))

	def validate_vehicle_item(self, doc=None):
		for d in self.invoices:
			super(VehicleInvoiceMovement, self).validate_vehicle_item(d)

	def validate_vehicle(self, doc=None):
		for d in self.invoices:
			super(VehicleInvoiceMovement, self).validate_vehicle(d)

	def validate_vehicle_booking_order(self, doc=None):
		for d in self.invoices:
			super(VehicleInvoiceMovement, self).validate_vehicle_booking_order(d)

	def set_vehicle_registration_order(self):
		for d in self.invoices:
			if self.purpose in ('Issue', 'Return'):
				d.vehicle_registration_order = get_vehicle_registration_order(d.vehicle)
			else:
				d.vehicle_registration_order = None

	def validate_vehicle_registration_order(self, doc=None):
		for d in self.invoices:
			# if self.purpose in ('Issue', 'Return'):
			# 	if self.issued_for == "Registration" and not d.vehicle_registration_order:
			# 		frappe.throw(_("Row #{0}: Vehicle Registration Order is mandatory for Registration {1}")
			# 			.format(d.idx, self.purpose))
			super(VehicleInvoiceMovement, self).validate_vehicle_registration_order(d)

	def update_vehicle_invoice(self, doc=None, update_vehicle=True):
		if self.purpose == "Receive":
			if self.docstatus == 1:
				self.create_received_vehicle_invoices()
			else:
				self.cancel_received_vehicle_invoices()
		else:
			update_vehicle = self.purpose != 'Transfer'
			for d in self.invoices:
				super(VehicleInvoiceMovement, self).update_vehicle_invoice(d, update_vehicle=update_vehicle)

	def update_vehicle_booking_order_invoice(self, doc=None):
		if self.purpose in ['Transfer', 'Receive']:
			return

		for d in self.invoices:
			super(VehicleInvoiceMovement, self).update_vehicle_booking_order_invoice(d)

	def update_vehicle_booking_order_registration(self, doc=None):
		if self.issued_for != "Registration":
			return

		for d in self.invoices:
			super(VehicleInvoiceMovement, self).update_vehicle_booking_order_registration(d)

	def update_vehicle_registration_order(self, doc=None):
		if self.purpose in ['Transfer', 'Receive']:
			return

		for d in self.invoices:
			super(VehicleInvoiceMovement, self).update_vehicle_registration_order(d)

	def create_received_vehicle_invoices(self):
		for d in self.invoices:
			doc = frappe.new_doc("Vehicle Invoice")
			doc.flags.from_vehicle_invoice_movement = True
			doc.vehicle_invoice_movement = self.name

			doc.posting_date = self.posting_date
			doc.remarks = self.remarks
			doc.supplier = self.supplier
			doc.supplier_name = self.supplier_name
			doc.received_by = self.employee
			doc.received_by_name = self.employee_name
			doc.vehicle = d.vehicle
			doc.item_code = d.item_code
			doc.vehicle_booking_order = d.vehicle_booking_order
			doc.bill_no = d.bill_no
			doc.bill_date = d.bill_date

			doc.save()
			doc.submit()

	def cancel_received_vehicle_invoices(self):
		invoices = frappe.get_all("Vehicle Invoice", filters={
			'vehicle_invoice_movement': self.name,
			'docstatus': 1
		})

		for d in invoices:
			doc = frappe.get_doc("Vehicle Invoice", d.name)
			doc.cancel()
