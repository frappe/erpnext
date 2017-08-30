# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils import cint, fmt_money, flt
from erpnext.accounts.doctype.pricing_rule.pricing_rule import get_pricing_rule_for_item

def get_qty_in_stock(item_code, item_warehouse_field):
	in_stock, stock_qty = 0, ''
	template_item_code = frappe.db.get_value("Item", item_code, "variant_of")

	warehouse = frappe.db.get_value("Item", item_code, item_warehouse_field)
	if not warehouse and template_item_code and template_item_code != item_code:
		warehouse = frappe.db.get_value("Item", template_item_code, item_warehouse_field)

	if warehouse:
		stock_qty = frappe.db.sql("""select actual_qty from tabBin where
			item_code=%s and warehouse=%s""", (item_code, warehouse))
		if stock_qty:
			in_stock = stock_qty[0][0] > 0 and 1 or 0

	return frappe._dict({"in_stock": in_stock, "stock_qty": stock_qty})

def get_price(item_code, price_list, customer_group, company, qty=1):
	template_item_code = frappe.db.get_value("Item", item_code, "variant_of")

	if price_list:
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
				"customer_group": customer_group,
				"company": company,
				"conversion_rate": 1,
				"for_shopping_cart": True
			}))

			if pricing_rule:
				if pricing_rule.pricing_rule_for == "Discount Percentage":
					price[0].price_list_rate = flt(price[0].price_list_rate * (1.0 - (flt(pricing_rule.discount_percentage) / 100.0)))

				if pricing_rule.pricing_rule_for == "Price":
					price[0].price_list_rate = pricing_rule.price_list_rate

			price_obj = price[0]
			if price_obj:
				price_obj["formatted_price"] = fmt_money(price_obj["price_list_rate"], currency=price_obj["currency"])

				price_obj["currency_symbol"] = not cint(frappe.db.get_default("hide_currency_symbol")) \
					and (frappe.db.get_value("Currency", price_obj.currency, "symbol") or price_obj.currency) \
					or ""

				if not price_obj["price_list_rate"]:
					price_obj["price_list_rate"] = 0

				if not price_obj["currency"]:
					price_obj["currency"] = ""

				if not price_obj["formatted_price"]:
					price_obj["formatted_price"] = ""

			return price_obj
