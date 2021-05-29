# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.vehicles.vehicle_booking_controller import VehicleBookingController

class VehicleQuotation(VehicleBookingController):
	def get_feed(self):
		customer = self.get('party_name') or self.get('financer')
		return _("To {0} | {1}").format(self.get("customer_name") or customer, self.get("item_name") or self.get("item_code"))

	def validate(self):
		super(VehicleQuotation, self).validate()

		self.set_title()
		self.get_terms_and_conditions()

		self.set_status()

	def on_cancel(self):
		self.db_set('status', 'Cancelled')

	def set_title(self):
		self.title = self.customer_name
