# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, cstr
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController
from erpnext.vehicles.utils import format_vehicle_id


class VehicleRegistrationReceipt(VehicleTransactionController):
	def get_feed(self):
		return _("For {0} | {1}").format(self.get("customer_name") or self.get('customer'), self.get("vehicle_license_plate"))

	def validate(self):
		super(VehicleRegistrationReceipt, self).validate()

		self.validate_duplicate_registration_receipt()
		self.set_vehicle_registration_order()
		self.validate_vehicle_registration_order()
		self.validate_registration_number()
		self.validate_call_date()
		self.set_title()

	def before_submit(self):
		self.validate_vehicle_mandatory()

	def on_submit(self):
		self.update_vehicle_details()
		self.update_vehicle_registration_order()
		self.update_vehicle_booking_order_registration()
		self.update_vehicle_booking_order_transfer_customer()
		self.make_vehicle_log()

	def on_cancel(self):
		self.update_vehicle_registration_order()
		self.update_vehicle_booking_order_registration()
		self.update_vehicle_booking_order_transfer_customer()
		self.cancel_vehicle_log()

	def set_title(self):
		self.title = "{0} - {1}".format(self.get('vehicle_license_plate'), self.get('customer_name') or self.get('customer'))

	def validate_duplicate_registration_receipt(self):
		registration_receipt = frappe.db.get_value("Vehicle Registration Receipt",
			filters={"vehicle": self.vehicle, "docstatus": 1, "name": ['!=', self.name]})

		if registration_receipt:
			frappe.throw(_("Registration Receipt for {0} has already been received in {1}")
				.format(frappe.get_desk_link("Vehicle", self.vehicle),
				frappe.get_desk_link("Vehicle Registration Receipt", registration_receipt)))

	def validate_registration_number(self):
		self.vehicle_license_plate = format_vehicle_id(self.vehicle_license_plate)

	def validate_call_date(self):
		if self.call_date and self.posting_date:
			if getdate(self.call_date) < getdate(self.posting_date):
				frappe.throw(_("Call Date cannot be before Received Date"))

	def update_vehicle_details(self):
		vehicle_doc = frappe.get_doc("Vehicle", self.vehicle)
		vehicle_doc.unregistered = 0
		vehicle_doc.license_plate = self.vehicle_license_plate
		vehicle_doc.save(ignore_permissions=True)


def get_vehicle_registration_receipt(vehicle=None, fields='name', as_dict=False):
	vehicle_registration_receipt = None

	if vehicle:
		vehicle_registration_receipt = frappe.db.get_value("Vehicle Registration Receipt", filters={
			'vehicle': vehicle,
			'docstatus': 1
		}, fieldname=fields, as_dict=as_dict)

	return vehicle_registration_receipt
