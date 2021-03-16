# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.controllers.vehicle_transaction_controller import VehicleTransactionController

class VehicleDelivery(VehicleTransactionController):
	def get_feed(self):
		return _("To {0} | {1}").format(self.get("customer_name") or self.get('customer'),
			self.get("item_name") or self.get("item_code"))

	def validate(self):
		super(VehicleDelivery, self).validate()

		self.set_title()

	def on_submit(self):
		self.update_stock_ledger()
		self.update_vehicle_booking_order()

	def on_cancel(self):
		self.update_stock_ledger()
		self.update_vehicle_booking_order()

	def set_title(self):
		self.title = "{0}{1}".format(self.customer_name or self.customer, ' ({0})'.format(self.get('received_by')) if self.get('received_by') else '')
