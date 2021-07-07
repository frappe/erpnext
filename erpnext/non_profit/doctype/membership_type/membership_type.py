# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _

class MembershipType(Document):
	def validate(self):
		if self.linked_item:
			is_stock_item = frappe.db.get_value("Item", self.linked_item, "is_stock_item")
			if is_stock_item:
				frappe.throw(_("The Linked Item should be a service item"))

def get_membership_type(razorpay_id):
	return frappe.db.exists("Membership Type", {"razorpay_plan_id": razorpay_id})