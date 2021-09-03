# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
import frappe

from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import (
	get_shopping_cart_settings,
)
from erpnext.e_commerce.doctype.item_review.item_review import get_item_reviews
from erpnext.e_commerce.doctype.website_item.website_item import check_if_user_is_customer


def get_context(context):
	context.body_class = "product-page"
	context.no_cache = 1
	context.full_page = True
	context.reviews = None

	if frappe.form_dict and frappe.form_dict.get("web_item"):
		context.web_item = frappe.form_dict.get("web_item")
		context.user_is_customer = check_if_user_is_customer()
		context.enable_reviews = get_shopping_cart_settings().enable_reviews

		if context.enable_reviews:
			reviews_data = get_item_reviews(context.web_item)
			context.update(reviews_data)
