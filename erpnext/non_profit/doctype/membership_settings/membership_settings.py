# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.integrations.utils import get_payment_gateway_controller
from frappe.model.document import Document

class MembershipSettings(Document):
	def generate_webhook_key(self):
		key = frappe.generate_hash(length=20)
		self.webhook_secret = key
		self.save()

		frappe.msgprint(
			_("Here is your webhook secret, this will be shown to you only once.") + "<br><br>" + key,
			_("Webhook Secret")
		);

	def revoke_key(self):
		self.webhook_secret = None;
		self.save()

	def get_webhook_secret(self):
		return self.get_password(fieldname="webhook_secret", raise_exception=False)

@frappe.whitelist()
def get_plans_for_membership(*args, **kwargs):
	controller = get_payment_gateway_controller("Razorpay")
	plans = controller.get_plans()
	return [plan.get("item") for plan in plans.get("items")]