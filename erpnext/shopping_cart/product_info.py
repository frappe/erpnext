# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils import cint
from erpnext.shopping_cart.cart import _get_cart_quotation
from erpnext.shopping_cart.doctype.shopping_cart_settings.shopping_cart_settings \
	import is_cart_enabled, get_shopping_cart_settings, show_quantity_in_website
from erpnext.utilities.product import get_price, get_qty_in_stock

@frappe.whitelist(allow_guest=True)
def get_product_info_for_website(item_code):
	"""get product price / stock info for website"""

	cart_quotation = _get_cart_quotation()
	cart_settings = get_shopping_cart_settings()

	price = get_price(
		item_code,
		cart_quotation.selling_price_list,
		cart_settings.default_customer_group,
		cart_settings.company
	)

	stock_status = get_qty_in_stock(item_code, "website_warehouse")

	product_info = {
		"price": price,
		"stock_qty": stock_status.stock_qty,
		"in_stock": stock_status.in_stock if stock_status.is_stock_item else 1,
		"qty": 0,
		"uom": frappe.db.get_value("Item", item_code, "stock_uom"),
		"show_stock_qty": show_quantity_in_website(),
		"sales_uom": frappe.db.get_value("Item", item_code, "sales_uom"),
		"show_availability_status": cint(frappe.db.get_single_value('Products Settings', 'show_availability_status'))
	}

	if product_info["price"]:
		if frappe.session.user != "Guest":
			item = cart_quotation.get({"item_code": item_code})
			if item:
				product_info["qty"] = item[0].qty

	return {
		"product_info": product_info,
		"cart_settings": cart_settings
	}

def set_product_info_for_website(item):
	"""set product price uom for website"""
	product_info = get_product_info_for_website(item.item_code)

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