# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, add_days, cint, date_diff
from frappe.model.mapper import get_mapped_doc
from erpnext.vehicles.vehicle_booking_controller import VehicleBookingController
from erpnext.crm.doctype.lead.lead import get_customer_from_lead


class VehicleQuotation(VehicleBookingController):
	def __init__(self, *args, **kwargs):
		super(VehicleQuotation, self).__init__(*args, **kwargs)
		self.status_map = [
			["Draft", None],
			["Open", "eval:self.docstatus==1"],
			["Lost", "eval:self.status=='Lost'"],
			["Ordered", "has_vehicle_booking_order"],
			["Cancelled", "eval:self.docstatus==2"],
		]

	def get_feed(self):
		customer = self.get('party_name') or self.get('financer')
		return _("To {0} | {1}").format(self.get("customer_name") or customer, self.get("item_name") or self.get("item_code"))

	def validate(self):
		super(VehicleQuotation, self).validate()

		self.validate_vehicle_qty()
		self.validate_quotation_valid_till()
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

	def onload(self):
		super(VehicleQuotation, self).onload()
		if self.quotation_to == "Customer":
			self.set_onload('customer', self.party_name)
		elif self.quotation_to == "Lead":
			self.set_onload('customer', get_customer_from_lead(self.party_name))

	def before_print(self):
		super(VehicleQuotation, self).before_print()
		self.total_discount = -self.total_discount

	def validate_vehicle_qty(self):
		if self.get('vehicle') and cint(self.qty) > 1:
			frappe.throw(_("Qty must be 1 if Vehicle is selected"))

	def set_title(self):
		self.title = self.customer_name

	def has_vehicle_booking_order(self):
		return frappe.db.get_value("Vehicle Booking Order", {"vehicle_quotation": self.name, "docstatus": 1})

	def update_opportunity(self, reopen=False):
		if self.get("opportunity"):
			opp = frappe.get_doc("Opportunity", self.opportunity)
			opp.set_status(update=True, status="Open" if reopen else None)
			opp.notify_update()

	def update_lead(self):
		if self.quotation_to == "Lead" and self.party_name:
			doc = frappe.get_doc("Lead", self.party_name)
			doc.set_status(update=True)
			doc.notify_update()

	@frappe.whitelist()
	def set_is_lost(self, is_lost, lost_reasons_list=None, detailed_reason=None):
		is_lost = cint(is_lost)

		if is_lost and self.has_vehicle_booking_order():
			frappe.throw(_("Cannot declare as Lost because Vehicle Quotation is converted to order"))

		if is_lost:
			self.set_status(update=True, status="Lost")

			if detailed_reason:
				self.db_set('order_lost_reason', detailed_reason)

			for reason in lost_reasons_list or []:
				row = self.append('lost_reasons', reason)
				row.db_insert()
		else:
			self.set_status(update=True, status="Open")
			self.db_set('order_lost_reason', None)
			self.lost_reasons = []
			self.update_child_table("lost_reasons")

		self.update_opportunity(reopen=not is_lost)
		self.update_lead()

		self.notify_update()


@frappe.whitelist()
def make_vehicle_booking_order(source_name, target_doc=None):
	quotation = frappe.db.get_value("Vehicle Quotation", source_name, ["transaction_date", "valid_till"], as_dict=1)
	if quotation.valid_till and (quotation.valid_till < quotation.transaction_date or quotation.valid_till < getdate(nowdate())):
		frappe.throw(_("Validity period of this quotation has ended."))
	return _make_vehicle_booking_order(source_name, target_doc)


def _make_vehicle_booking_order(source_name, target_doc=None, ignore_permissions=False):
	from erpnext.selling.doctype.quotation.quotation import get_customer_from_quotation

	def set_missing_values(source, target):
		customer = get_customer_from_quotation(source)
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
				"delivery_date": "delivery_date",
				"vehicle": "vehicle",
				"opportunity": "opportunity"
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


def set_expired_status():
	frappe.db.sql("""
		UPDATE
			`tabVehicle Quotation` SET `status` = 'Expired'
		WHERE
			`status` not in ('Ordered', 'Expired', 'Lost', 'Cancelled') AND `valid_till` < %s AND `docstatus` = 1
		""", (nowdate()))
