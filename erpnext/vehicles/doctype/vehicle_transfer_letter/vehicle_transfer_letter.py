# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController


class VehicleTransferLetter(VehicleTransactionController):
	def get_feed(self):
		return _("To {0} | {1}").format(self.get("customer_name") or self.get('customer'),
			self.get("item_name") or self.get("item_code"))

	def validate(self):
		super(VehicleTransferLetter, self).validate()
		self.validate_same_owner()

		self.set_title()

	def on_submit(self):
		self.update_vehicle_party_details()
		self.update_vehicle_booking_order()

	def on_cancel(self):
		self.update_vehicle_party_details()
		self.update_vehicle_booking_order()

	def validate_same_owner(self):
		if self.customer == self.vehicle_owner:
			frappe.throw(_("New Owner and Previous Owner cannot be the same"))

	def update_vehicle_party_details(self):
		if self.serial_no:
			sr_no = frappe.get_doc("Serial No", self.serial_no)
			last_sle = sr_no.get_last_sle()
			sr_no.set_party_details(last_sle.get("purchase_sle"), last_sle.get("delivery_sle"))
			sr_no.save(ignore_permissions=True)

	def update_vehicle_booking_order(self):
		if self.get('vehicle_booking_order'):
			vbo = frappe.get_doc("Vehicle Booking Order", self.vehicle_booking_order)
			vbo.update_transfer_customer(update=True)
			vbo.notify_update()

	def set_title(self):
		self.title = "{0} ({1})".format(self.customer_name or self.customer, self.get_previous_owner_name())

	def get_previous_owner_name(self):
		return self.get('booking_customer_name') or self.get('vehicle_owner_name') \
			or self.get('vehicle_owner') or self.get('company')
