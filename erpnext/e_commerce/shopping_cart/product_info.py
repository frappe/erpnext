# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.e_commerce.shopping_cart.cart import _get_cart_quotation, _set_price_list
from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import (
	get_shopping_cart_settings,
	show_quantity_in_website
)
from erpnext.utilities.product import get_price, get_web_item_qty_in_stock, get_non_stock_item_status

@frappe.whitelist(allow_guest=True)
def get_product_info_for_website(item_code, skip_quotation_creation=False):
	"""get product price / stock info for website"""

	cart_settings = get_shopping_cart_settings()
	if not cart_settings.enabled:
		return frappe._dict()

	cart_quotation = frappe._dict()
	if not skip_quotation_creation:
		cart_quotation = _get_cart_quotation()

	selling_price_list = cart_quotation.get("selling_price_list") if cart_quotation else _set_price_list(cart_settings, None)

	price = get_price(
		item_code,
		selling_price_list,
		cart_settings.default_customer_group,
		cart_settings.company
	)
	stock_status = get_web_item_qty_in_stock(item_code, "website_warehouse")

	product_info = {
		"price": price,
		"stock_qty": stock_status.stock_qty,
		"in_stock": stock_status.in_stock if stock_status.is_stock_item else get_non_stock_item_status(item_code, "website_warehouse"),
		"qty": 0,
		"uom": frappe.db.get_value("Item", item_code, "stock_uom"),
		"show_stock_qty": show_quantity_in_website(),
		"sales_uom": frappe.db.get_value("Item", item_code, "sales_uom")
	}

	if product_info["price"]:
		if frappe.session.user != "Guest":
			item = cart_quotation.get({"item_code": item_code}) if cart_quotation else None
			if item:
				product_info["qty"] = item[0].qty

	return frappe._dict({
		"product_info": product_info,
		"cart_settings": cart_settings
	})

def set_product_info_for_website(item):
	"""set product price uom for website"""
	product_info = get_product_info_for_website(item.item_code, skip_quotation_creation=True).get("product_info")

	if product_info:
		item.update(product_info)
		item["stock_uom"] = product_info.get("uom")
		item["sales_uom"] = product_info.get("sales_uom")
		if product_info.get("price"):
			item["price_stock_uom"] = product_info.get("price").get("formatted_price")
			item["price_sales_uom"] = product_info.get("price").get("formatted_price_sales_uom")
		else:
			item["price_stock_uom"] = ""
			item["price_sales_uom"] = ""
