# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json, os, redis

from frappe.model.document import Document
from frappe.utils import cint, expand_relative_urls, fmt_money, flt, add_years, add_to_date, now, get_datetime, get_datetime_str
from frappe import _
from erpnext.utilities.product import get_price, get_qty_in_stock

hub_url = "http://erpnext.hub:8000"
# hub_url = "http://hub.erpnext.org"

class HubSetupError(frappe.ValidationError): pass

class HubSettings(Document):
	config_args = ['enabled']
	profile_args = ['hub_user_email', 'hub_user_name', 'country']
	seller_args = ['company', 'seller_city', 'site_name', 'seller_description']
	publishing_args = ['publish', 'current_item_fields', 'publish_pricing',
		'selling_price_list', 'publish_availability', 'warehouse']

	base_fields_for_items = ["item_code", "item_name", "item_group", "description", "image", "stock_uom",
		 "modified"]

	item_fields_to_update = ["price", "currency", "stock_qty"]

	def onload(self):
		if not self.site_name:
			# TODO: remove port for production
			self.site_name = "http://" + frappe.local.site + ":8000"

	def validate(self):
		if self.publish_pricing and not self.selling_price_list:
			frappe.throw(_("Please select a Price List to publish pricing"))

	def on_update(self):
		if not self.access_token:
			if self.enabled:
				frappe.throw(_("Enabled without access token"))
			return

		# If just registered
		if self.enabled != self.get_doc_before_save().enabled and self.enabled == 1:
			return

		self.update_hub()

	def update_hub(self):
		self.update_profile_settings()
		self.update_publishing()

	def update_profile_settings(self):
		send_hub_request('update_user_details',
			data=self.get_args(self.profile_args + self.seller_args + self.publishing_args))

	def update_publishing(self):
		if self.publish != self.get_doc_before_save().publish:
			if self.publish:
				self.publish_all_set_items()
			else:
				self.reset_publishing_settings()
				self.unpublish_all_items()

	def publish_all_set_items(self, verbose=True):
		"""Publish items hub.erpnext.org"""
		# A way to set 'publish in hub' for a bulk of items, if not all are by default

		item_list = frappe.db.sql_list("select name from tabItem where publish_in_hub=1")
		items = frappe.db.get_all("Item", fields=self.base_fields_for_items + ["hub_warehouse"], filters={"publish_in_hub": 1})
		if not items:
			frappe.msgprint(_("No published items found."))
			return

		for item in items:
			item.modified = get_datetime_str(item.modified)
			if item.image:
				item.image = self.site_name + item.image

			set_stock_qty(item)

			if self.publish_pricing:
				set_item_price(item, self.company, self.selling_price_list)
			else:
				item.price = 0
				item.currency = None

		response_msg = send_hub_request('update_items',
			data={
			"items_to_update": json.dumps(items),
			"item_list": json.dumps(item_list),
			"item_fields": self.base_fields_for_items + self.item_fields_to_update
		})

		if verbose:
			frappe.msgprint(_("{0} Items synced".format(len(items))))

		# sync_item_fields_at_hub()

	def unpublish_all_items(self):
		"""Unpublish from hub.erpnext.org, delete items there"""
		send_hub_request('delete_all_items_of_user')

	### Account
	def register(self):
		"""Register at hub.erpnext.org and exchange keys"""
		# if self.access_token or hasattr(self, 'private_key'):
		# 	return
		response = requests.post(hub_url + "/api/method/hub.hub.api."+"register",
			data = { "args_data": json.dumps(self.get_args(
				self.config_args + self.profile_args + self.seller_args #['public_key_pem']
			))}
		)
		response.raise_for_status()
		response_msg = response.json().get("message")

		self.access_token = response_msg.get("access_token")

		# Set start values
		self.last_sync_datetime = add_years(now(), -10)
		self.current_item_fields = json.dumps(self.base_fields_for_items + self.item_fields_to_update)

	def unregister_from_hub(self):
		"""Unpublish, then delete transactions and user from there"""
		self.reset_publishing_settings()
		send_hub_request('unregister')

	### Helpers
	def get_args(self, arg_list):
		args = {}
		for d in arg_list:
			args[d] = self.get(d)
		return args

	def reset_publishing_settings(self):
		self.publish = 0
		self.publish_pricing = 0
		self.publish_availability = 0
		self.current_item_fields = json.dumps(self.base_fields_for_items + self.item_fields_to_update)

	def set_publish_for_selling_items(self):
		"""Set `publish_in_hub`=1 for all Sales Items"""
		for item in frappe.get_all("Item", fields=["name"],
			filters={ "publish_in_hub": 0, "is_sales_item": 1}):
			frappe.db.set_value("Item", item.name, "publish_in_hub", 1)

def send_hub_request(method, data = [], now = False):
	if now:
		return hub_request(method, data)
	try:
		frappe.enqueue('erpnext.hub_node.doctype.hub_settings.hub_settings.hub_request', now=now,
			api_method=method, data=data)
		return 1
	except redis.exceptions.ConnectionError:
		return hub_request(method, data)

def hub_request(api_method, data = []):
	hub = frappe.get_single("Hub Settings")
	response = requests.post(hub_url + "/api/method/hub.hub.api." + "call_method",
		data = {
			"access_token": hub.access_token,
			"method": api_method,
			"message": json.dumps(data)
		}
	)
	response.raise_for_status()
	return response.json().get("message")

def validate_hub_settings(doc, method):
	frappe.get_doc("Hub Settings", "Hub Settings").run_method("validate")

def get_hub_settings():
	if not getattr(frappe.local, "hub_settings", None):
		frappe.local.hub_settings = frappe.get_doc("Hub Settings", "Hub Settings")
	return frappe.local.hub_settings

def is_hub_enabled():
	return get_hub_settings().enabled

def is_hub_published():
	return get_hub_settings().publish

def is_pricing_published():
	return get_hub_settings().publish_pricing

def get_hub_selling_price_list():
	return get_hub_settings().selling_price_list

def is_availability_published():
	return get_hub_settings().publish_availability

def check_hub_enabled():
	if not get_hub_settings().enabled:
		frappe.throw(_("You need to enable Hub"), HubSetupError)

def get_item_fields_to_sync():
	return ["price", "currency", "stock_qty"]

def sync_item_fields_at_hub():
	# Only updates dynamic feilds of price and stock
	items = frappe.db.get_all("Item", fields=["item_code", "hub_warehouse"], filters={"publish_in_hub": 1})

	for item in items:
		set_stock_qty(item)

		hub_settings = get_hub_settings()
		if is_pricing_published():
			set_item_price(item, hub_settings.company, hub_settings.selling_price_list)
		else:
			item.price = 0
			item.currency = None

	response_msg = send_hub_request('update_item_fields',
		data={
			"items_with_fields_updates": json.dumps(items),
			"fields_to_update": get_item_fields_to_sync()
		}
	)
	# hub_settings = get_hub_settings()
	# hub_settings.set("last_sync_datetime", response_msg["last_sync_datetime"])
	# hub_settings.save()

	frappe.msgprint(_("Field values synced"))

def set_item_price(item, company, selling_price_list):
	item_code = item.item_code
	price = get_price(item_code, selling_price_list, "Commercial", company)
	item.price = price["price_list_rate"]
	item.currency = price["currency"]

def set_stock_qty(item):
	item.stock_qty = get_qty_in_stock(item.item_code, "hub_warehouse").stock_qty
