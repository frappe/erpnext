# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController

class VehicleReceipt(VehicleTransactionController):
	def get_feed(self):
		return _("From {0} | {1}").format(self.get("suplier_name") or self.get('supplier'),
			self.get("item_name") or self.get("item_code"))

	def validate(self):
		super(VehicleReceipt, self).validate()
		self.set_title()

	def before_submit(self):
		super(VehicleReceipt, self).before_submit()
		self.validate_transporter()

	def on_submit(self):
		self.update_vehicle_details()
		self.update_stock_ledger()
		self.update_vehicle_booking_order()

	def on_cancel(self):
		self.update_stock_ledger()
		self.update_vehicle_booking_order()

	def set_title(self):
		party = self.get('customer_name') or self.get('customer') or self.get('supplier_name') or self.get('supplier')
		self.title = "{0}{1}".format(self.item_name or self.item_code, ' ({0})'.format(party) if party else '')

	def validate_transporter(self):
		if self.get('transporter') and not self.get('lr_no'):
			frappe.throw(_("Transport Receipt No (Bilty) is mandatory when receiving from Transporter"))

	def update_vehicle_details(self):
		if self.vehicle_warranty_no:
			frappe.db.set_value("Vehicle", self.vehicle, "warranty_no", self.vehicle_warranty_no)
