# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils import cint, fmt_money, flt
from erpnext.shopping_cart.cart import _get_cart_quotation
from erpnext.shopping_cart.doctype.shopping_cart_settings.shopping_cart_settings \
	import is_cart_enabled, get_shopping_cart_settings, show_quantity_in_website
from erpnext.accounts.doctype.pricing_rule.pricing_rule import get_pricing_rule_for_item

@frappe.whitelist(allow_guest=True)
def get_product_info(item_code):
	"""get product price / stock info"""
	if not is_cart_enabled():
		return {}

	qty = 0
	cart_quotation = _get_cart_quotation()
	template_item_code = frappe.db.get_value("Item", item_code, "variant_of")
	stock_status = get_qty_in_stock(item_code, template_item_code)
	in_stock = stock_status.in_stock
	stock_qty = stock_status.stock_qty
	price = get_price(item_code, template_item_code, cart_quotation.selling_price_list)

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
		"stock_qty": stock_qty,
		"in_stock": in_stock,
		"uom": frappe.db.get_value("Item", item_code, "stock_uom"),
		"qty": qty,
		"show_stock_qty": show_quantity_in_website()
	}

def get_qty_in_stock(item_code, template_item_code):
	warehouse = frappe.db.get_value("Item", item_code, "website_warehouse")
	if not warehouse and template_item_code and template_item_code != item_code:
		warehouse = frappe.db.get_value("Item", template_item_code, "website_warehouse")

	if warehouse:
		stock_qty = frappe.db.sql("""select actual_qty from tabBin where
			item_code=%s and warehouse=%s""", (item_code, warehouse))
		if stock_qty:
			in_stock = stock_qty[0][0] > 0 and 1 or 0
		else:
			in_stock = 0

	return frappe._dict({"in_stock": in_stock, "stock_qty": stock_qty})

def get_price(item_code, template_item_code, price_list, qty=1):
	if price_list:
		cart_settings = get_shopping_cart_settings()

		price = frappe.get_all("Item Price", fields=["price_list_rate", "currency"],
			filters={"price_list": price_list, "item_code": item_code})

		if template_item_code and not price:
			price = frappe.get_all("Item Price", fields=["price_list_rate", "currency"],
				filters={"price_list": price_list, "item_code": template_item_code})

		if price:
			pricing_rule = get_pricing_rule_for_item(frappe._dict({
				"item_code": item_code,
				"qty": qty,
				"transaction_type": "selling",
				"price_list": price_list,
				"customer_group": cart_settings.default_customer_group,
				"company": cart_settings.company,
				"conversion_rate": 1,
				"for_shopping_cart": True
			}))

			if pricing_rule:
				if pricing_rule.pricing_rule_for == "Discount Percentage":
					price[0].price_list_rate = flt(price[0].price_list_rate * (1.0 - (pricing_rule.discount_percentage / 100.0)))

				if pricing_rule.pricing_rule_for == "Price":
					price[0].price_list_rate = pricing_rule.price_list_rate

			return price[0]
