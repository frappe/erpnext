# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController


class VehicleReceipt(VehicleTransactionController):
	def get_feed(self):
		if self.get('customer') and self.get('supplier'):
			return _("For {0} | {1}").format(self.get("customer_name") or self.get('customer'),
				self.get("item_name") or self.get("item_code"))
		else:
			return _("From {0} | {1}").format(self.get("suplier_name") or self.get('supplier') or self.get("customer_name") or self.get('customer'),
				self.get("item_name") or self.get("item_code"))

	def validate(self):
		super(VehicleReceipt, self).validate()
		self.validate_party_mandatory()
		self.validate_readings()
		self.set_title()

	def before_submit(self):
		self.validate_vehicle_mandatory()
		self.validate_transporter()

	def on_submit(self):
		self.update_stock_ledger()
		self.update_vehicle_warranty_no()
		self.update_vehicle_booking_order_delivery()
		self.make_vehicle_log()

	def on_cancel(self):
		self.update_stock_ledger()
		self.update_vehicle_booking_order_delivery()
		self.cancel_vehicle_log()

	def set_title(self):
		party = self.get('customer_name') or self.get('customer') or self.get('supplier_name') or self.get('supplier')
		self.title = "{0} - {1}".format(party, self.item_name or self.item_code)

	def validate_transporter(self):
		if self.get('transporter') and not self.get('lr_no'):
			frappe.throw(_("Transport Receipt No (Bilty) is mandatory when receiving from Transporter"))

	def validate_readings(self):
		if flt(self.fuel_level) < 0 or flt(self.fuel_level) > 100:
			frappe.throw(_("Fuel Level must be between 0% and 100%"))
		if cint(self.keys) < 0:
			frappe.throw(_("No of Keys cannot be negative"))
