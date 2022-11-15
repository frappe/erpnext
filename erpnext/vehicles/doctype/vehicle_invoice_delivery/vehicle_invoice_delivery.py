# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, cint
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController
from erpnext.vehicles.doctype.vehicle_invoice.vehicle_invoice import get_vehicle_invoice_details,\
	get_vehicle_invoice


class VehicleInvoiceDelivery(VehicleTransactionController):
	def get_feed(self):
		return _("To {0} | {1}").format(self.get("customer_name") or self.get('customer'), self.get("bill_no"))

	def validate(self):
		super(VehicleInvoiceDelivery, self).validate()

		self.validate_party_mandatory()
		self.validate_duplicate_invoice_delivery()
		self.set_vehicle_invoice_details()
		self.validate_vehicle_invoice()
		self.set_vehicle_registration_order()
		self.validate_vehicle_registration_order()
		self.set_title()

	def before_submit(self):
		self.validate_vehicle_mandatory()
		self.validate_invoice_not_received()

	def on_submit(self):
		if cint(self.is_copy):
			self.update_vehicle_invoice_copy_delivered()
		else:
			self.update_vehicle_invoice()
			self.update_vehicle_booking_order_invoice()
			self.update_vehicle_registration_order()

	def on_cancel(self):
		if cint(self.is_copy):
			self.update_vehicle_invoice_copy_delivered()
		else:
			self.update_vehicle_invoice()
			self.update_vehicle_booking_order_invoice()
			self.update_vehicle_registration_order()

	def set_title(self):
		self.title = "{0} - {1}".format(self.get('customer_name') or self.get('customer'), self.get('bill_no'))

	def validate_duplicate_invoice_delivery(self):
		if cint(self.is_copy):
			return

		invoice_delivery = frappe.db.get_value("Vehicle Invoice Delivery",
			filters={"vehicle": self.vehicle, "docstatus": 1, "is_copy": 0, "name": ['!=', self.name]})

		if invoice_delivery:
			frappe.throw(_("Invoice for {0} has already been delivered in {1}")
				.format(frappe.get_desk_link("Vehicle", self.vehicle),
				frappe.get_desk_link("Vehicle Invoice Delivery", invoice_delivery)))

	def set_vehicle_invoice_details(self):
		self.vehicle_invoice = get_vehicle_invoice(self.vehicle)

		invoice_details = get_vehicle_invoice_details(self.vehicle_invoice)
		for k, v in invoice_details.items():
			if self.meta.has_field(k):
				self.set(k, v)

	def validate_vehicle_invoice(self):
		if self.vehicle_invoice:
			received_date = frappe.db.get_value("Vehicle Invoice", self.vehicle_invoice, 'posting_date')
			if getdate(self.posting_date) < getdate(received_date):
				frappe.throw(_("Invoice Delivery Date cannot be before Invoice Received Date {0}")
					.format(frappe.bold(frappe.format(getdate(received_date)))))

	def validate_invoice_not_received(self):
		if not self.vehicle_invoice:
			frappe.throw(_("Invoice for {0} has not yet been received")
				.format(frappe.get_desk_link('Vehicle', self.vehicle)))

	def update_vehicle_invoice_copy_delivered(self):
		if self.vehicle_invoice:
			vinvr = frappe.get_doc("Vehicle Invoice", self.vehicle_invoice)
			vinvr.update_copy_delivered()
			vinvr.notify_update()


@frappe.whitelist()
def get_default_documents(vehicle_details):
	out = []

	settings = frappe.get_cached_doc("Vehicles Settings", None)
	for d in settings.get('invoice_documents'):
		row = frappe._dict({
			'document_name': d.document_name,
			'is_included': d.is_included,
		})
		if d.if_registered and not vehicle_details.license_plate:
			row.is_included = 0

		out.append(row)

	return out
