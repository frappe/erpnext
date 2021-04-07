# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

no_cache = 1

import frappe
from erpnext.e_commerce.doctype.item_review.item_review import get_item_reviews

def get_context(context):
	context.full_page = True
	context.reviews = None
	if frappe.form_dict and frappe.form_dict.get("item_code"):
		context.item_code = frappe.form_dict.get("item_code")
		context.web_item = frappe.db.get_value("Website Item", {"item_code": context.item_code}, "name")
		get_item_reviews(context.web_item, 0, 10, context)
