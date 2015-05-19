# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils import cint, fmt_money, cstr
from erpnext.shopping_cart.cart import _get_cart_quotation
from urllib import unquote

@frappe.whitelist(allow_guest=True)
def get_product_info(item_code):
	"""get product price / stock info"""
	if not cint(frappe.db.get_default("shopping_cart_enabled")):
		return {}

	cart_quotation = _get_cart_quotation()

	price_list = cstr(unquote(frappe.local.request.cookies.get("selling_price_list")))

	warehouse = frappe.db.get_value("Item", item_code, "website_warehouse")
	if warehouse:
		in_stock = frappe.db.sql("""select actual_qty from tabBin where
			item_code=%s and warehouse=%s""", (item_code, warehouse))
		if in_stock:
			in_stock = in_stock[0][0] > 0 and 1 or 0
	else:
		in_stock = -1

	price = price_list and frappe.db.sql("""select price_list_rate, currency from
		`tabItem Price` where item_code=%s and price_list=%s""",
		(item_code, price_list), as_dict=1) or []

	price = price and price[0] or None
	qty = 0

	if price:
		price["formatted_price"] = fmt_money(price["price_list_rate"], currency=price["currency"])

		price["currency"] = not cint(frappe.db.get_default("hide_currency_symbol")) \
			and (frappe.db.get_value("Currency", price.currency, "symbol") or price.currency) \
			or ""

		if frappe.session.user != "Guest":
			item = cart_quotation.get({"item_code": item_code})
			if item:
				qty = item[0].qty

	return {
		"price": price,
		"stock": in_stock,
		"uom": frappe.db.get_value("Item", item_code, "stock_uom"),
		"qty": qty
	}
