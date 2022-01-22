# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController

class VehicleReceipt(VehicleTransactionController):
	def get_feed(self):
		if self.get('customer') and self.get('supplier'):
			return _("For {0} | {1}").format(self.get("customer_name") or self.get('customer'),
				self.get("item_name") or self.get("item_code"))
		else:
			return _("From {0} | {1}").format(self.get("suplier_name") or self.get('supplier') or self.get("customer_name") or self.get('customer'),
				self.get("item_name") or self.get("item_code"))

	def set_missing_values(self, doc=None, for_validate=False):
		super(VehicleReceipt, self).set_missing_values(doc, for_validate)
		self.set_missing_checklist()

	def validate(self):
		super(VehicleReceipt, self).validate()
		self.validate_party_mandatory()
		self.set_title()

	def before_submit(self):
		self.validate_vehicle_mandatory()
		self.validate_transporter()

	def on_submit(self):
		self.update_stock_ledger()
		self.update_vehicle_warranty_no()
		self.make_odometer_log()
		self.update_vehicle_booking_order_delivery()

	def on_cancel(self):
		self.update_stock_ledger()
		self.cancel_odometer_log()
		self.update_vehicle_booking_order_delivery()

	def set_title(self):
		party = self.get('customer_name') or self.get('customer') or self.get('supplier_name') or self.get('supplier')
		self.title = "{0} - {1}".format(party, self.item_name or self.item_code)

	def validate_transporter(self):
		if self.get('transporter') and not self.get('lr_no'):
			frappe.throw(_("Transport Receipt No (Bilty) is mandatory when receiving from Transporter"))

	def set_missing_checklist(self):
		if not self.vehicle_checklist:
			checklist = get_vehicle_checklist_default_items()
			for d in checklist:
				self.append("vehicle_checklist", {'checklist_item': d.checklist_item, 'checklist_item_checked': 0})


@frappe.whitelist()
def get_vehicle_checklist_default_items():
	vehicles_settings = frappe.get_cached_doc("Vehicles Settings", None)
	checklist_items = [d.checklist_item for d in vehicles_settings.vehicle_checklist_items]
	return checklist_items
