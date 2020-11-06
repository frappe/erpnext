# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe

class MembershipType(Document):
	pass

def get_membership_type(razorpay_id):
	return frappe.db.exists("Membership Type", {"razorpay_plan_id": razorpay_id})