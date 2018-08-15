# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.utilities.product import get_price

class SubscriptionPlan(Document):
	def validate(self):
		self.validate_interval_count()

	def validate_interval_count(self):
		if self.billing_interval_count < 1:
			frappe.throw('Billing Interval Count cannot be less than 1')

@frappe.whitelist()
def get_plan_rate(plan, quantity=1, customer=None):
	plan = frappe.get_doc("Subscription Plan", plan)
	if plan.price_determination == "Fixed rate":
		return plan.cost

	elif plan.price_determination == "Based on price list":
		if customer:
			customer_group = frappe.db.get_value("Customer", customer, "customer_group")
		else:
			customer_group = None
		
		price = get_price(item_code=plan.item, price_list=plan.price_list, customer_group=customer_group, company=None, qty=quantity)
		if not price:
			return 0
		else:
			return price.price_list_rate
