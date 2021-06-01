# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, add_days, cint, date_diff
from frappe.model.mapper import get_mapped_doc
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
		if cint(self.quotation_validity_days) < 0:
			frappe.throw(_("Quotation Validity Days cannot be negative"))

		if cint(self.quotation_validity_days):
			self.valid_till = add_days(getdate(self.transaction_date), cint(self.quotation_validity_days) - 1)
		if not cint(self.quotation_validity_days) and self.valid_till:
			self.quotation_validity_days = date_diff(self.valid_till, self.transaction_date) + 1

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
			self.set_status(update=True, status='Lost')

			if detailed_reason:
				frappe.db.set(self, 'order_lost_reason', detailed_reason)

			self.lost_reasons = []
			for reason in lost_reasons_list:
				self.append('lost_reasons', reason)

			self.update_opportunity()
			self.update_lead()
			self.save()

		else:
			frappe.throw(_("Cannot set as Lost as Vehicle Booking Order is made."))


@frappe.whitelist()
def make_vehicle_booking_order(source_name, target_doc=None):
	quotation = frappe.db.get_value("Vehicle Quotation", source_name, ["transaction_date", "valid_till"], as_dict=1)
	if quotation.valid_till and (quotation.valid_till < quotation.transaction_date or quotation.valid_till < getdate(nowdate())):
		frappe.throw(_("Validity period of this quotation has ended."))
	return _make_sales_order(source_name, target_doc)


def _make_sales_order(source_name, target_doc=None, ignore_permissions=False):
	def set_missing_values(source, target):
		customer = _make_customer(source, ignore_permissions)
		if customer:
			target.customer = customer.name
			target.customer_name = customer.customer_name

		target.flags.ignore_permissions = ignore_permissions
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_payment_schedule")
		target.run_method("set_due_date")

	doclist = get_mapped_doc("Vehicle Quotation", source_name, {
		"Vehicle Quotation": {
			"doctype": "Vehicle Booking Order",
			"validation": {
				"docstatus": ["=", 1]
			},
			"field_map": {
				"name": "vehicle_quotation",
				"remarks": "remarks",
				"delivery_period": "delivery_period",
				"color": "color_1",
				"delivery_date": "delivery_date"
			},
			"field_no_map": ['tc_name', 'terms']
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		},
		"Payment Schedule": {
			"doctype": "Payment Schedule",
			"add_if_empty": True
		}
	}, target_doc, set_missing_values, ignore_permissions=ignore_permissions)

	return doclist


def _make_customer(quotation, ignore_permissions=False):
	if quotation and quotation.get('party_name'):
		if quotation.get('quotation_to') == 'Lead':
			lead_name = quotation.get("party_name")
			customer_name = frappe.db.get_value("Customer", {"lead_name": lead_name},
				["name", "customer_name"], as_dict=True)

			if not customer_name:
				from erpnext.crm.doctype.lead.lead import _make_customer
				customer_doclist = _make_customer(lead_name, ignore_permissions=ignore_permissions)
				customer = frappe.get_doc(customer_doclist)
				customer.flags.ignore_permissions = ignore_permissions

				try:
					customer.insert()
					return customer
				except frappe.MandatoryError as e:
					mandatory_fields = e.args[0].split(':')[1].split(',')
					mandatory_fields = [customer.meta.get_label(field.strip()) for field in mandatory_fields]

					frappe.local.message_log = []
					lead_link = frappe.utils.get_link_to_form("Lead", lead_name)
					message = _("Could not auto create Customer due to the following missing mandatory field(s):") + "<br>"
					message += "<br><ul><li>" + "</li><li>".join(mandatory_fields) + "</li></ul>"
					message += _("Please create Customer from Lead {0}.").format(lead_link)

					frappe.throw(message, title=_("Mandatory Missing"))
			else:
				return customer_name
		else:
			return frappe.get_cached_doc("Customer", quotation.get("party_name"))


def set_expired_status():
	frappe.db.sql("""
		UPDATE
			`tabVehicle Quotation` SET `status` = 'Expired'
		WHERE
			`status` not in ('Ordered', 'Expired', 'Lost', 'Cancelled') AND `valid_till` < %s
		""", (nowdate()))
