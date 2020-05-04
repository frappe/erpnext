# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.integrations.utils import get_payment_gateway_controller
from frappe.model.document import Document

class MembershipSettings(Document):
	pass

@frappe.whitelist()
def get_plans_for_membership(*args, **kwargs):
	controller = get_payment_gateway_controller("Razorpay")
	plans = controller.get_plans()
	return [plan.get("item") for plan in plans.get("items")]