# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

no_cache = 1

import frappe
from erpnext.utilities.product import get_price
from erpnext.e_commerce.shopping_cart.cart import _set_price_list

def get_context(context):
	settings = frappe.get_doc("E Commerce Settings")
	items = get_wishlist_items()
	selling_price_list = _set_price_list(settings)

	for item in items:
		if settings.show_stock_availability:
			item.available = get_stock_availability(item.item_code, item.get("warehouse"))

		price_details = get_price(
			item.item_code,
			selling_price_list,
			settings.default_customer_group,
			settings.company
		)

		if price_details:
			item.formatted_mrp = price_details.get('formatted_mrp')
			if item.formatted_mrp:
				item.discount = price_details.get('formatted_discount_percent') or \
					price_details.get('formatted_discount_rate')

	context.items = items
	context.settings = settings

def get_stock_availability(item_code, warehouse):
	stock_qty = frappe.utils.flt(
		frappe.db.get_value("Bin",
			{
				"item_code": item_code,
				"warehouse": warehouse
			},
			"actual_qty")
	)
	return True if stock_qty else False

def get_wishlist_items():
	if frappe.db.exists("Wishlist", frappe.session.user):
		return frappe.db.sql("""
			Select
				item_code, item_name, website_item, price,
				warehouse, image, item_group, route, formatted_price
			from
				`tabWishlist Items`
			where
				parent=%(user)s""" % {"user": frappe.db.escape(frappe.session.user)}, as_dict=1)
	return