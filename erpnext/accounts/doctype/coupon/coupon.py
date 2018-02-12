# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Coupon(Document):
	pass

@frappe.whitelist()
def apply_coupon_price_list(coupon):
	if coupon:
		coupon_doc = frappe.get_doc("Coupon", coupon)
		if coupon_doc.coupon_price_list:
			return coupon_doc.coupon_price_list