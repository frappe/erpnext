# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class MembershipType(Document):
	def validate(self):
		if self.linked_item:
			is_stock_item = frappe.db.get_value("Item", self.linked_item, "is_stock_item")
			if is_stock_item:
				frappe.throw(_("The Linked Item should be a service item"))


def get_membership_type(razorpay_id):
	return frappe.db.exists("Membership Type", {"razorpay_plan_id": razorpay_id})
