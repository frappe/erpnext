# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

no_cache = 1

import frappe

def get_context(context):
	settings = frappe.get_doc("E Commerce Settings")
	items = get_wishlist_items()

	if settings.show_stock_availability:
		for item in items:
			stock_qty = frappe.utils.flt(
				frappe.db.get_value("Bin",
					{
						"item_code": item.item_code,
						"warehouse": item.get("warehouse")
					},
					"actual_qty")
				)
			item.available = True if stock_qty else False

	context.items = items
	context.settings = settings

def get_wishlist_items():
	if frappe.db.exists("Wishlist", frappe.session.user):
		return frappe.db.sql("""
			Select
				item_code, item_name, website_item, price,
				warehouse, image, item_group, route, formatted_price
			from
				`tabWishlist Items`
			where
				parent=%(user)s"""%{"user": frappe.db.escape(frappe.session.user)}, as_dict=1)
	return