# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class PromotionsClaims(Document):
	pass
	def before_submit(self):
		if self.status =='Pending':
			frappe.throw(_("Select statue Approved or Rejected"))


@frappe.whitelist()
def make_promotion_decision(source_name, target=None):
	target = get_mapped_doc("Promotions Claims", source_name, {
		"Promotions Claims": {
			"doctype": "Promotion Decision",
			"field_map": {
				"employee": "employee"
			}
		}
	})
	return target
