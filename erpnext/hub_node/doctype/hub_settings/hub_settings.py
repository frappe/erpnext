# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json
from frappe.model.document import Document
from frappe.utils import cint, expand_relative_urls, fmt_money, flt, add_years, now, get_datetime, get_datetime_str
from frappe import _
from erpnext.accounts.doctype.pricing_rule.pricing_rule import get_pricing_rule_for_item


class HubSettings(Document):
	hub_url = "http://hub.ch:8000"
	# hub_url = "http://hub.erpnext.org"
	def validate(self):
		if self.enabled:
			if not self.password:
				self.register()
			else:
				self.update_user_details()

			if self.publish and self.password:
				self.publish_selling_items()

		if not self.enabled and self.password:
			self.update_user_details()

		if not self.publish and self.password:
			self.unpublish()

		if not self.last_sync_datetime:
			self.last_sync_datetime = add_years(now(), -10)

	def register(self):
		"""Register at hub.erpnext.org, save auto generated `password`"""
		response = requests.post(self.hub_url + "/api/method/hub.hub.api.register", data=self.get_args())
		response.raise_for_status()
		response = response.json()
		self.password = response.get("message").get("password")

	def publish_selling_items(self):
		"""Set `publish_in_hub`=1 for all Sales Items"""
		for item in frappe.get_all("Item", fields=["name"],
			filters={ "publish_in_hub": 0, "is_sales_item": 1}):
			frappe.db.set_value("Item", item.name, "publish_in_hub", 1)

	def unpublish(self):
		"""Unpublish from hub.erpnext.org"""
		response = requests.post(self.hub_url + "/api/method/hub.hub.api.unpublish", data={
			"password": self.password
		})
		response.raise_for_status()

	def update_user_details(self):
		"""Update details at hub.erpnext.org"""
		args = self.get_args()
		if self.password:
			response = requests.post(self.hub_url + "/api/method/hub.hub.api.update_user_details", data={
				"password": self.password,
				"args": json.dumps(args)
			})
			response.raise_for_status()

	def get_args(self):
		return {
			"enabled": self.enabled,
			"hub_user_name": self.hub_user_name,
			"company": self.company,
			"country": self.country,
			"email": self.email,
			"publish": self.publish,
			"seller_city": self.seller_city,
			"seller_website": self.seller_website,
			"seller_description": self.seller_description,
			"publish_pricing": self.publish_pricing,
			"selling_price_list": self.selling_price_list,
			"publish_availability": self.publish_availability,
			"warehouse": self.warehouse
		}

	def sync(self, verbose=True):
		"""Sync items with hub.erpnext.org"""
		if not self.publish:
			if verbose:
				frappe.msgprint(_("Publish to sync items"))
			return
		items = frappe.db.get_all("Item",
			fields=["name", "item_code", "item_name", "description", "image", "item_group", "stock_uom", "modified"],
			filters={"publish_in_hub": 1})
		
		for item in items:
			if item.modified > get_datetime(self.last_sync_datetime):
				item.to_sync = 1
			item.modified = get_datetime_str(item.modified)
			if item.image:
				item.image = expand_relative_urls(item.image)

			item = self.get_item_details(item)	
		items_to_update = [a for a in items if a.to_sync == 1]

		item_list = frappe.db.sql_list("select name from tabItem where publish_in_hub=1")

		data = {"password": self.password, "items_to_update": json.dumps(items_to_update), "item_list": json.dumps(item_list) }
		print data, "data"
		if items:
			response = requests.post(self.hub_url + "/api/method/hub.hub.api.sync", data={
				"password": self.password,
				"items_to_update": json.dumps(items_to_update),
				"item_list": json.dumps(item_list)
			})
			print response
			response.raise_for_status()
			response = response.json()
			self.last_sync_datetime = response.get("message").get("last_sync_datetime")
			
			if verbose:
				frappe.msgprint(_("{0} Items synced".format(len(items))))
		else:
			if verbose:
				frappe.msgprint(_("Items already synced"))

	def get_item_details(self, item):
		item_code = item.item_code
		template_item_code = frappe.db.get_value("Item", item_code, "variant_of")
	
		item = get_qty_in_stock(item, template_item_code, self.warehouse, self.last_sync_datetime)
		item = get_price(item, template_item_code, self.selling_price_list, self.company, self.last_sync_datetime)
		return item

def get_qty_in_stock(item, template_item_code, warehouse, last_sync_datetime):
	item_code = item.item_code
	if not warehouse and template_item_code and template_item_code != item_code:
		warehouse = frappe.db.get_value("Item", template_item_code, warehouse)

	if warehouse:
		stock_qty = frappe.db.sql("""select actual_qty from tabBin where
			item_code=%s and warehouse=%s and modified > %s""", (item_code, warehouse, last_sync_datetime))
		if stock_qty:
			stock_qty = stock_qty[0][0]
	else:
		stock_qty = 0

	if stock_qty:
		item.stock_qty = stock_qty
		item.to_sync = 1

	return item

def get_price(item, template_item_code, price_list, company, last_sync_datetime, qty=1):
	item_code = item.item_code

	if price_list:
		price = frappe.get_all("Item Price", fields=["price_list_rate", "currency"],
			filters={"price_list": price_list, "item_code": item_code, "selling": 1, "modified": (">",last_sync_datetime)})

		if not price and template_item_code:
			price = frappe.get_all("Item Price", fields=["price_list_rate", "currency"],
				filters={"price_list": price_list, "item_code": template_item_code, "selling": 1, "modified": (">",last_sync_datetime)})

		if price or frappe.db.exists({"doctype": "Pricing Rule", "for_price_list": price_list, "modified": (">",last_sync_datetime)}):
			pricing_rule = get_pricing_rule_for_item(frappe._dict({
				"item_code": item_code,
				"qty": qty,
				"transaction_type": "selling",
				"price_list": price_list,
				"company": company,
				"conversion_rate": 1
			}))

			if pricing_rule:
				if pricing_rule.pricing_rule_for == "Discount Percentage":
					price[0].price_list_rate = flt(price[0].price_list_rate * (1.0 - (pricing_rule.discount_percentage / 100.0)))

				if pricing_rule.pricing_rule_for == "Price":
					price[0].price_list_rate = pricing_rule.price_list_rate	
		if price:
			price = price[0]
			price["formatted_price"] = fmt_money(price["price_list_rate"], currency=price["currency"])
			price["currency"] = not cint(frappe.db.get_default("hide_currency_symbol")) \
				and (frappe.db.get_value("Currency", price.currency, "symbol") or price.currency) \
				or ""
			item.price = price.formatted_price
			item.to_sync = 1

	return item