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

		if not self.enabled or (hasattr(self, 'just_registered') and self.just_registered):
			self.just_registered = 0
			return

		if hasattr(self, 'in_callback') and self.in_callback:
			self.in_callback = 0
			return

		if self.suspended:
			# show a tag
			pass

		self.update_hub()

	def update_hub(self):
		self.update_profile_settings()
		self.update_publishing()

	def update_profile_settings(self):
		make_and_enqueue_message(msg_type='HUB-USER-UPDATE', method='update_user_details',
			data=self.get_args(self.profile_args + self.seller_args + self.publishing_args),
			callback='erpnext.hub_node.doctype.hub_settings.hub_settings.set_last_sync_datetime')

	def update_publishing(self):
		if self.publish != self._doc_before_save.publish:
			if self.publish:
				self.publish_all_set_items()
			else:
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

		make_and_enqueue_message(msg_type='HUB-ITEMS-UPDATE', method='update_items',
			data={
			"items_to_update": json.dumps(items),
			"item_list": json.dumps(item_list),
			"item_fields": self.base_fields_for_items + self.item_fields_to_update
		})

		# if verbose:
		# 	frappe.msgprint(_("{0} Items synced".format(len(items))))

		# sync_item_fields_at_hub()

	def unpublish_all_items(self):
		"""Unpublish from hub.erpnext.org, delete items there"""
		make_and_enqueue_message(msg_type='HUB-ITEMS-DELETE-ALL', method='delete_all_items_of_user', now = True,
			callback='erpnext.hub_node.doctype.hub_settings.hub_settings.reset_hub_publishing_settings')

	### Account
	def register(self):
		"""Register at hub.erpnext.org and exchange keys"""
		response = requests.post(hub_url + "/api/method/hub.hub.api."+"register",
			data = { "args_data": json.dumps(self.get_args(
				self.config_args + self.profile_args + self.seller_args
			))}
		)
		response.raise_for_status()
		response_msg = response.json().get("message")

		access_token = response_msg.get("access_token")
		if access_token:
			self.access_token = access_token
			self.enabled = 1
			self.last_sync_datetime = add_years(now(), -10)
			self.current_item_fields = json.dumps(self.base_fields_for_items + self.item_fields_to_update)

			# flag
			self.just_registered = 1

			self.save()
		else:
			frappe.throw(_("Sorry, we can't register you at this time."))

	def unregister_from_hub(self):
		"""Unpublish, then delete transactions and user from there"""
		make_and_enqueue_message(msg_type='HUB-USER-UNREG', method='unregister_user', now = True,
			callback='erpnext.hub_node.doctype.hub_settings.hub_settings.reset_hub_settings')

	### Helpers
	def get_args(self, arg_list):
		args = {}
		for d in arg_list:
			args[d] = self.get(d)
		return args

	def reset_enable(self):
		self.enabled = 0
		self.access_token = ""

	def reset_publishing_settings(self, last_sync_datetime = ""):
		self.publish = 0
		self.publish_pricing = 0
		self.publish_availability = 0
		self.selling_price_list = ""
		self.current_item_fields = json.dumps([])
		self.last_sync_datetime = get_datetime(last_sync_datetime) or add_years(now(), -10)

	def set_publish_for_selling_items(self):
		"""Set `publish_in_hub`=1 for all Sales Items"""
		for item in frappe.get_all("Item", fields=["name"],
			filters={ "publish_in_hub": 0, "is_sales_item": 1}):
			frappe.db.set_value("Item", item.name, "publish_in_hub", 1)

def make_and_enqueue_message(msg_type, method, data=[], callback="", callback_args={}, now = 0):
	message = frappe.new_doc("Outgoing Hub Message")

	message.type = msg_type
	message.method = method
	message.arguments = json.dumps(data)
	message.callback = callback
	message.callback_args = json.dumps(callback_args)
	message.now = now

	message.save(ignore_permissions=True)

###########################
def send_hub_request(method, data = "", now = False, callback = "", callback_args = {}):
	if now:
		hub_request(method, data, callback, callback_args)
		return
	try:
		frappe.enqueue('erpnext.hub_node.doctype.hub_settings.hub_settings.hub_request', now=now,
			api_method=method, data=data, callback=callback, callback_args=callback_args)
	except redis.exceptions.ConnectionError:
		hub_request(method, data, callback, callback_args)
#########################

def hub_request(message_id, api_method, data = "", callback = "", callback_args = {}):
	hub = frappe.get_single("Hub Settings")
	response = requests.post(hub_url + "/api/method/hub.hub.api." + "call_method",
		data = {
			"access_token": hub.access_token,
			"method": api_method,
			"message": data,
			# TODO: switch off debug mode
			"debug": True
		}
	)
	print("]]]]]]]]]]]]]]]]]")
	response.raise_for_status()
	print("=================")

	callback_args = json.loads(callback_args)
	response_msg = response.json().get("message")
	if response_msg:
		frappe.db.set_value("Outgoing Hub Message", message_id, "status", "Successful")
		# Deleting mechanism for successful messages?, or logging
		callback_args.update(response_msg)
		frappe.enqueue(callback, now=True, **callback_args)

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

def set_last_sync_datetime(last_sync_datetime):
	doc = get_hub_settings()
	doc.last_sync_datetime = get_datetime(last_sync_datetime)
	doc.in_callback = 1
	doc.save()

def reset_hub_publishing_settings(last_sync_datetime = ""):
	doc = get_hub_settings()
	doc.reset_publishing_settings(last_sync_datetime)
	doc.in_callback = 1
	doc.save()

def reset_hub_settings(last_sync_datetime = ""):
	doc = get_hub_settings()
	doc.reset_publishing_settings(last_sync_datetime)
	doc.reset_enable()
	doc.in_callback = 1
	doc.save()
	frappe.msgprint(_("Successfully unregistered."))

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

	make_and_enqueue_message(msg_type='HUB-ITEMS-FIELDS-UPDATE', method='update_item_fields',
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
