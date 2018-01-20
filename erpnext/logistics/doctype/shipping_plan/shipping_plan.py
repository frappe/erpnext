# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import scrub, _
from frappe.utils import cint
from erpnext.logistics.controller.fedex_controller import FedExController

class ShippingPlan(Document):
	def __init__(self, *args, **kwargs):
		super(ShippingPlan, self).__init__(*args, **kwargs)
		self.controller = FedExController(args=self)

	def validate(self):
		self.controller.validate()
		self.validate_delivery_note()
		self.validate_items_mandatory()
		self.validate_for_existing_shipping_plan()

	def validate_delivery_note(self):
		'''validate if delivery note has status as draft'''
		if cint(frappe.db.get_value("Delivery Note", self.delivery_note, "docstatus")) != 0:
			frappe.throw(_("Delivery Note {0} must not be submitted").format(self.delivery_note))

	def validate_items_mandatory(self):
		if not len(self.items):
			frappe.msgprint(_("No Items for Shipping Plan"), raise_exception=1)

	def validate_for_existing_shipping_plan(doc, method):
		# check if Shipping Plan is already created against self.delivery_note
		shipping_plan = frappe.db.get_value("Shipping Plan", {"name":["not in", [self.name]],\
			"delivery_note":self.delivery_note, "docstatus":["in", ["0"]]}, "name")
		if shipping_plan:
			frappe.throw(_("Shipping Plan {0} already created against delivery note {1}.".\
				format(shipping_plan, self.delivery_note)))
