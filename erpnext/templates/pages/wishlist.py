# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
import frappe

from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import (
	get_shopping_cart_settings,
)
from erpnext.e_commerce.shopping_cart.cart import _set_price_list
from erpnext.utilities.product import get_price


def get_context(context):
	is_guest = frappe.session.user == "Guest"

	settings = get_shopping_cart_settings()
	items = get_wishlist_items() if not is_guest else []
	selling_price_list = _set_price_list(settings) if not is_guest else None

	items = set_stock_price_details(items, settings, selling_price_list)

	context.body_class = "product-page"
	context.items = items
	context.settings = settings
	context.no_cache = 1


def get_stock_availability(item_code, warehouse):
	from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses

	if warehouse and frappe.get_cached_value("Warehouse", warehouse, "is_group") == 1:
		warehouses = get_child_warehouses(warehouse)
	else:
		warehouses = [warehouse] if warehouse else []

	stock_qty = 0.0
	for warehouse in warehouses:
		stock_qty += frappe.utils.flt(
			frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty")
		)

	return bool(stock_qty)


def get_wishlist_items():
	if not frappe.db.exists("Wishlist", frappe.session.user):
		return []

	return frappe.db.get_all(
		"Wishlist Item",
		filters={"parent": frappe.session.user},
		fields=[
			"web_item_name",
			"item_code",
			"item_name",
			"website_item",
			"warehouse",
			"image",
			"item_group",
			"route",
		],
	)


def set_stock_price_details(items, settings, selling_price_list):
	for item in items:
		if settings.show_stock_availability:
			item.available = get_stock_availability(item.item_code, item.get("warehouse"))

		price_details = get_price(
			item.item_code, selling_price_list, settings.default_customer_group, settings.company
		)

		if price_details:
			item.formatted_price = price_details.get("formatted_price")
			item.formatted_mrp = price_details.get("formatted_mrp")
			if item.formatted_mrp:
				item.discount = price_details.get("formatted_discount_percent") or price_details.get(
					"formatted_discount_rate"
				)

	return items
