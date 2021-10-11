# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.contacts.doctype.contact.contact import get_default_contact
from frappe.model.document import Document
from frappe.utils import flt, get_time

from erpnext.accounts.party import get_party_shipping_address


class Shipment(Document):
	def validate(self):
		self.validate_weight()
		self.validate_pickup_time()
		self.set_value_of_goods()
		if self.docstatus == 0:
			self.status = 'Draft'

	def on_submit(self):
		if not self.shipment_parcel:
			frappe.throw(_('Please enter Shipment Parcel information'))
		if self.value_of_goods == 0:
			frappe.throw(_('Value of goods cannot be 0'))
		self.db_set('status', 'Submitted')

	def on_cancel(self):
		self.db_set('status', 'Cancelled')

	def validate_weight(self):
		for parcel in self.shipment_parcel:
			if flt(parcel.weight) <= 0:
				frappe.throw(_('Parcel weight cannot be 0'))

	def validate_pickup_time(self):
		if self.pickup_from and self.pickup_to and get_time(self.pickup_to) < get_time(self.pickup_from):
			frappe.throw(_("Pickup To time should be greater than Pickup From time"))

	def set_value_of_goods(self):
		value_of_goods = 0
		for entry in self.get("shipment_delivery_note"):
			value_of_goods += flt(entry.get("grand_total"))
		self.value_of_goods = value_of_goods if value_of_goods else self.value_of_goods

@frappe.whitelist()
def get_address_name(ref_doctype, docname):
	# Return address name
	return get_party_shipping_address(ref_doctype, docname)

@frappe.whitelist()
def get_contact_name(ref_doctype, docname):
	# Return address name
	return get_default_contact(ref_doctype, docname)

@frappe.whitelist()
def get_company_contact(user):
	contact = frappe.db.get_value('User', user, [
		'first_name',
		'last_name',
		'email',
		'phone',
		'mobile_no',
		'gender',
	], as_dict=1)
	if not contact.phone:
		contact.phone = contact.mobile_no
	return contact
