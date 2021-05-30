# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, nowdate
from erpnext.vehicles.vehicle_booking_controller import VehicleBookingController

class VehicleQuotation(VehicleBookingController):
	def get_feed(self):
		customer = self.get('party_name') or self.get('financer')
		return _("To {0} | {1}").format(self.get("customer_name") or customer, self.get("item_name") or self.get("item_code"))

	def validate(self):
		super(VehicleQuotation, self).validate()

		self.update_opportunity()
		self.validate_valid_till()
		self.get_terms_and_conditions()

		self.set_title()
		self.set_status()

	def on_submit(self):
		self.update_opportunity()
		self.update_lead()

	def on_cancel(self):
		self.db_set('status', 'Cancelled')
		self.update_opportunity()
		self.update_lead()

	def set_title(self):
		self.title = self.customer_name

	def validate_valid_till(self):
		if self.valid_till and getdate(self.valid_till) < getdate(self.transaction_date):
			frappe.throw(_("Valid till date cannot be before transaction date"))

	def has_vehicle_booking_order(self):
		return frappe.db.get_value("Vehicle Booking Order", {"vehicle_quotation": self.name, "docstatus": 1})

	def update_opportunity(self):
		if self.opportunity:
			self.update_opportunity_status()

	def update_lead(self):
		if self.quotation_to == "Lead" and self.party_name:
			frappe.get_doc("Lead", self.party_name).set_status(update=True)

	def update_opportunity_status(self):
		opp = frappe.get_doc("Opportunity", self.opportunity)
		opp.set_status(update=True)

	def declare_enquiry_lost(self, lost_reasons_list, detailed_reason=None):
		if not self.has_vehicle_booking_order():
			frappe.db.set(self, 'status', 'Lost')

			if detailed_reason:
				frappe.db.set(self, 'order_lost_reason', detailed_reason)

			for reason in lost_reasons_list:
				self.append('lost_reasons', reason)

			self.update_opportunity()
			self.update_lead()
			self.save()

		else:
			frappe.throw(_("Cannot set as Lost as Vehicle Booking Order is made."))


def set_expired_status():
	frappe.db.sql("""
		UPDATE
			`tabVehicle Quotation` SET `status` = 'Expired'
		WHERE
			`status` not in ('Ordered', 'Expired', 'Lost', 'Cancelled') AND `valid_till` < %s
		""", (nowdate()))
