# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController

class VehicleInvoiceDelivery(VehicleTransactionController):
	def get_feed(self):
		return _("To {0} | {1}").format(self.get("customer_name") or self.get('customer'), self.get("bill_no"))

	def validate(self):
		super(VehicleInvoiceDelivery, self).validate()

		self.validate_duplicate_invoice_delivery()
		self.set_vehicle_invoice_receipt()
		self.validate_vehicle_invoice_receipt()
		self.set_title()

	def before_submit(self):
		super(VehicleInvoiceDelivery, self).before_submit()
		self.validate_invoice_not_received()

	def on_submit(self):
		self.update_vehicle_booking_order()

	def on_cancel(self):
		self.update_vehicle_booking_order()

	def set_vehicle_invoice_receipt(self):
		self.vehicle_invoice_receipt = get_vehicle_invoice_receipt(self.vehicle)
		self.update(get_vehicle_invoice_details(self.vehicle_invoice_receipt))

	def validate_vehicle_invoice_receipt(self):
		if self.vehicle_invoice_receipt:
			received_date = frappe.db.get_value("Vehicle Invoice Receipt", self.vehicle_invoice_receipt, 'posting_date')
			if getdate(self.posting_date) < getdate(received_date):
				frappe.throw(_("Invoice Delivery Date cannot be before Invoice Receive Date {0}")
					.format(frappe.bold(frappe.format(getdate(received_date)))))

	def validate_invoice_not_received(self):
		if not self.vehicle_invoice_receipt:
			frappe.throw(_("Invoice for {0} has not yet been received")
				.format(frappe.get_desk_link('Vehicle', self.vehicle)))

	def validate_duplicate_invoice_delivery(self):
		invoice_delivery = frappe.db.get_value("Vehicle Invoice Delivery",
			filters={"vehicle": self.vehicle, "docstatus": 1, "name": ['!=', self.name]})

		if invoice_delivery:
			frappe.throw(_("Invoice for {0} has already been delivered in {1}")
				.format(frappe.get_desk_link("Vehicle", self.vehicle),
				frappe.get_desk_link("Vehicle Invoice Delivery", invoice_delivery)))

	def set_title(self):
		self.title = "{0} ({1})".format(self.get('bill_no'), self.get('customer_name') or self.get('customer'))


@frappe.whitelist()
def get_vehicle_invoice_receipt(vehicle):
	if not vehicle:
		return None

	return frappe.db.get_value("Vehicle Invoice Receipt",
		filters={"vehicle": vehicle, "docstatus": 1})


@frappe.whitelist()
def get_vehicle_invoice_details(vehicle_invoice_receipt):
	invoice_details = frappe._dict()
	if vehicle_invoice_receipt:
		invoice_details = frappe.db.get_value("Vehicle Invoice Receipt", vehicle_invoice_receipt,
			['bill_no', 'bill_date'], as_dict=1) or frappe._dict()

	out = frappe._dict()
	out.bill_no = invoice_details.bill_no
	out.bill_date = invoice_details.bill_date

	return out
