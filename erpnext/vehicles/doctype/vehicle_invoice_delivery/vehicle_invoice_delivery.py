# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController

class VehicleInvoiceDelivery(VehicleTransactionController):
	def get_feed(self):
		return _("To {0} | {1}").format(self.get("customer_name") or self.get('customer'), self.get("bill_no"))

	def validate(self):
		super(VehicleInvoiceDelivery, self).validate()

		self.set_title()

	def on_submit(self):
		self.update_vehicle_booking_order()

	def on_cancel(self):
		self.update_vehicle_booking_order()

	def set_title(self):
		self.title = "{0} ({1})".format(self.get('bill_no'), self.get('customer_name') or self.get('customer'))
