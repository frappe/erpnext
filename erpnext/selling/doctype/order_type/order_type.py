# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import copy
from frappe.model.document import Document


class OrderType(Document):
	pass


@frappe.whitelist()
def get_order_type_defaults(order_type, company):
	if order_type:
		order_type_doc = frappe.get_cached_doc("Order Type", order_type)
		if order_type_doc:
			for d in order_type_doc.item_defaults or []:
				if d.company == company:
					row = copy.deepcopy(d.as_dict())
					row.pop("name")
					return row

	return frappe._dict()
