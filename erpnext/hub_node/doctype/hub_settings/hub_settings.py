# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json

from frappe.model.document import Document
from frappe.utils import add_years, now, get_datetime, get_datetime_str
from frappe import _
from erpnext.utilities.product import get_price, get_qty_in_stock
from six import string_types

hub_url = "http://erpnext.hub:8000"
# hub_url = "https://hub.erpnext.org"

batch_size = 200

class HubSetupError(frappe.ValidationError): pass

class HubSettings(Document):
	config_args = ['enabled']
	profile_args = ['hub_user', 'country']
	seller_args = ['company', 'seller_city', 'site_name', 'seller_description']
	publishing_args = ['publish', 'current_item_fields', 'publish_pricing',
		'selling_price_list', 'publish_availability', 'warehouse']

	base_fields_for_items = ["item_code", "item_name", "item_group", "description", "image", "stock_uom",
		 "modified"] # hub_category

	item_fields_to_update = ["price", "currency", "stock_qty"]

	def onload(self):
		if not self.site_name:
			# TODO: remove port for production
			self.site_name = "http://" + frappe.local.site + ":8000"

	def validate(self):
		if self.publish_pricing and not self.selling_price_list:
			frappe.throw(_("Please select a Price List to publish pricing"))

	def get_hub_url(self):
		return hub_url

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
		# self.update_publishing()

	def update_profile_settings(self):
		hub_request(
			method='update_user_details',
			data=self.get_args(self.profile_args + self.seller_args + self.publishing_args)
		)

	def sync_items(self):
		publish_item_count = frappe.db.count("Item", filters={"publish_in_hub": 1})
		start = 0

		while start < publish_item_count:
			items = frappe.db.get_all("Item",
				fields = self.base_fields_for_items + ["hub_warehouse"],
				filters ={"publish_in_hub": 1},
				limit_start = start,
				limit_page_length = batch_size,
				order_by='modified desc'
			)
			if not items:
				frappe.msgprint(_("No published items found."))
				return
			self.enqueue_item_batch(items)
			start += batch_size

	def enqueue_item_batch(self, items):
		item_list = []
		for item in items:
			item_list.append(item.item_code)
			item.modified = get_datetime_str(item.modified)
			if item.image:
				item.image = self.site_name + item.image

			set_stock_qty(item)

			if self.publish_pricing:
				set_item_price(item, self.company, self.selling_price_list)

		hub_request(
			method='hub.hub.doctype.hub_item.hub_item.sync_items',
			data={
				"items_to_update": json.dumps(items),
				"item_list": json.dumps(item_list),
				"item_fields": self.item_fields_to_update + self.base_fields_for_items
			})


	def update_publishing(self):
		if self.publish != self.get_doc_before_save().publish:
			if self.publish:
				frappe.enqueue('erpnext.hub_node.doctype.hub_settings.hub_settings.sync_items')

				self.current_item_fields = json.dumps(self.base_fields_for_items + self.item_fields_to_update)
			else:
				self.unpublish_all_items()
		else:
			if self.publish:
				fields = []
				if self.publish_pricing != self.get_doc_before_save().publish_pricing:
					if self.publish_pricing:
						fields += ["price", "currency", "formatted_price"]
				if self.publish_availability != self.get_doc_before_save().publish_availability:
					if self.publish_availability:
						fields += ["stock_qty"]
				if fields:
					frappe.enqueue('erpnext.hub_node.doctype.hub_settings.hub_settings.update_item_fields_at_hub',
						fields=fields)

	def unpublish_all_items(self):
		"""Unpublish from hub.erpnext.org, delete items there"""
		hub_request(
			method='delete_all_items_of_user',
			now = True)

	### Account
	def register(self):
		"""Register at hub.erpnext.org and exchange keys"""

		response = requests.post(hub_url + "/api/method/hub.hub.api.register",
			data = {"args_data": json.dumps(self.get_args(
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
		hub_request(
			method='unregister_user',
			now = True,
			callback='erpnext.hub_node.doctype.hub_settings.hub_settings.reset_hub_settings'
		)

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

def hub_request(method, data=None, callback=None, callback_args=None, now=False):
	if data and not isinstance(data, string_types):
		data = json.dumps(data)

	return frappe.get_doc(dict(
		doctype = 'Hub Message',
		method = method,
		data = data,
		callback = callback,
		callback_args = json.dumps(callback_args),
		now = now
	)).insert()

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

def get_current_item_fields():
	return json.loads(get_hub_settings().current_item_fields)

def check_hub_enabled():
	if not get_hub_settings().enabled:
		frappe.throw(_("You need to enable Hub"), HubSetupError)

def reset_hub_publishing_settings(last_sync_datetime = ""):
	doc = frappe.get_doc("Hub Settings", "Hub Settings")
	doc.reset_publishing_settings(last_sync_datetime)
	doc.in_callback = 1
	doc.save()

def reset_hub_settings(last_sync_datetime = ""):
	doc = frappe.get_doc("Hub Settings", "Hub Settings")
	doc.reset_publishing_settings(last_sync_datetime)
	doc.reset_enable()
	doc.in_callback = 1
	doc.save()
	frappe.msgprint(_("Successfully unregistered."))

@frappe.whitelist()
def sync_items():
	"""Publish items hub.erpnext.org"""
	# A way to set 'publish in hub' for a bulk of items, if not all are by default
	frappe.has_permission('Hub Settings', throw=True)
	frappe.enqueue_doc('Hub Settings', name=None, method='sync_items')

def update_item_fields_at_hub(fields):
	publish_item_count = frappe.db.count("Item", filters={"publish_in_hub": 1})
	start = 0

	while start < publish_item_count:
		items = frappe.db.get_all("Item", fields=["item_code", "hub_warehouse"], filters={"publish_in_hub": 1},
			limit_start = start, limit_page_length = batch_size, order_by='modified desc')
		enqueue_item_batch_with_fields(items, fields)
		start += batch_size

def enqueue_item_batch_with_fields(items, fields):
	for item in items:
		if "stock_qty" in fields:
			set_stock_qty(item)

		hub_settings = get_hub_settings()
		if "price" in fields:
			if is_pricing_published():
				set_item_price(item, hub_settings.company, hub_settings.selling_price_list)

	hub_request(
		method='update_item_fields',
		data={
			"items_with_fields_updates": json.dumps(items),
			"fields_to_update": json.dumps(fields)
		})

def sync_item_fields_at_hub():
	# Only updates dynamic feilds of price and stock
	items = frappe.db.get_all("Item", fields=["item_code", "hub_warehouse"], filters={"publish_in_hub": 1})
	fields = ["stock_qty"]

	for item in items:
		set_stock_qty(item)

		if is_pricing_published():
			fields += ["price", "currency", "formatted_price"]
			hub_settings = get_hub_settings()
			set_item_price(item, hub_settings.company, hub_settings.selling_price_list)

	hub_request(
		method='update_item_fields',
		data={
			"items_with_fields_updates": json.dumps(items),
			"fields_to_update": json.dumps(fields)
		})

def set_item_price(item, company, selling_price_list):
	item_code = item.item_code
	price = get_price(item_code, selling_price_list, "Commercial", company)
	item.price = price["price_list_rate"] if price else 0
	item.currency = price["currency"] if price else ""
	item.formatted_price = price["formatted_price"] if price else ""

def set_stock_qty(item):
	qty = get_qty_in_stock(item.item_code, "hub_warehouse").stock_qty
	item.stock_qty = qty[0][0] if qty else 0

