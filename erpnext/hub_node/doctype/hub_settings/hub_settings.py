# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json, os

from frappe.model.document import Document
from frappe.utils import cint, expand_relative_urls, fmt_money, flt, add_years, add_to_date, now, get_datetime, get_datetime_str
from frappe import _
from erpnext.accounts.doctype.pricing_rule.pricing_rule import get_pricing_rule_for_item

hub_url = "http://erpnext.hub:8000"
# hub_url = "http://hub.erpnext.org"

class HubSettings(Document):
	config_args = ['enabled']
	profile_args = ['hub_user_email', 'hub_user_name', 'country']
	only_in_code = ['private_key']
	seller_args = ['company', 'seller_city', 'site_name', 'seller_description']
	publishing_args = ['publish', 'publish_pricing', 'selling_price_list', 'publish_availability', 'warehouse']
	personal_args = ['hub_public_key_pem']

	base_fields_for_items = ["name", "item_code", "item_name", "description", "image", "item_group",
		 "modified"] #"price", "stock_uom", "stock_qty"

	def onload(self):
		if not self.site_name:
			# TODO: remove port for production
			self.site_name = "http://" + frappe.local.site + ":8000"

	def reset_current_on_save_flags(self):
		self.item_fields_to_add = []
		self.item_fields_to_remove = []
		self.publishing_changed = {
			"publish": 0,
			"publish_pricing": 0,
			"publish_availability": 0
		}

	def validate(self):
		self.reset_current_on_save_flags()
		self.update_settings_changes()
		if (self.publishing_changed["publish_pricing"] or
			self.publishing_changed["publish_availability"]):
			self.update_fields()

	def on_update(self):
		if not self.access_token:
			if self.enabled:
				frappe.throw(_("Enabled without access_token"))
			return

		# If just registered
		if self.enabled != self.get_doc_before_save().enabled and self.enabled == 1:
			return

		self.update_hub()
		self.update_item_fields_state()

	def update_settings_changes(self):
		# Pick publishing changes
		for setting in self.publishing_changed.keys():
			if self.get(setting) != self.get_doc_before_save().get(setting):
				self.publishing_changed[setting] = 1

	def update_fields(self):
		if self.publishing_changed["publish_pricing"]:
			# TODO: pricing
			fields = ["standard_rate"]
			if self.publish_pricing:
				self.item_fields_to_add += fields
			else:
				self.item_fields_to_remove += fields
		if self.publishing_changed["publish_availability"]:
			# fields = ["stock_uom", "stock_qty"]
			fields = ["stock_uom"]
			if self.publish_availability:
				self.item_fields_to_add += fields
			else:
				self.item_fields_to_remove += fields

	def update_item_fields_state(self):
		current_item_fields = json.loads(self.current_item_fields)
		current_item_fields += self.item_fields_to_add
		new_current_item_fields = [f for f in set(current_item_fields) if f not in self.item_fields_to_remove]
		self.current_item_fields = json.dumps(new_current_item_fields)

	def update_hub(self):
		# Updating profile call
		response_msg = send_hub_request('update_user_details',
			data=self.get_args(self.profile_args + self.seller_args))

		self.update_publishing()

	def update_publishing(self):
		if self.publishing_changed["publish"]:
			if self.publish:
				fields = json.loads(self.current_item_fields)
				fields += self.item_fields_to_add
				self.current_item_fields = json.dumps(fields)
				self.publish_all_set_items()
			else:
				self.reset_publishing_settings()
				self.unpublish_all_items()
		else:
			if self.item_fields_to_add:
				self.add_item_fields_at_hub()
			if self.item_fields_to_remove:
				self.remove_item_fields_at_hub()

	def publish_all_set_items(self, verbose=True):
		"""Publish items hub.erpnext.org"""
		# A way to set 'publish in hub' for a bulk of items, if not all are by default, like
		self.set_publish_for_selling_items()

		fields = json.loads(self.current_item_fields)

		items = frappe.db.get_all("Item", fields=fields, filters={"publish_in_hub": 1})
		if not items:
			frappe.msgprint(_("No published items found."))
			return

		for item in items:
			item.modified = get_datetime_str(item.modified)
			if item.image:
				item.image = self.site_name + item.image
		item_list = frappe.db.sql_list("select name from tabItem where publish_in_hub=1")

		response_msg = send_hub_request('update_items',
			data={
			"items_to_update": json.dumps(items),
			"item_list": json.dumps(item_list),
			"item_fields": fields
		})
		self.last_sync_datetime = response_msg.get("last_sync_datetime")

		if verbose:
			frappe.msgprint(_("{0} Items synced".format(len(items))))

	def unpublish_all_items(self):
		"""Unpublish from hub.erpnext.org, delete items there"""
		response_msg = send_hub_request('delete_all_items_of_user')

	def add_item_fields_at_hub(self):
		items = frappe.db.get_all("Item", fields=["item_code"] + self.item_fields_to_add, filters={"publish_in_hub": 1})
		response_msg = send_hub_request('add_item_fields',
			data={
				"items_with_new_fields": json.dumps(items),
				"fields_to_add": self.item_fields_to_add
			}
		)

	def remove_item_fields_at_hub(self):
		response_msg = send_hub_request('remove_item_fields',
			data={"fields_to_remove": self.item_fields_to_remove})

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
		self.current_item_fields = json.dumps(self.base_fields_for_items)
		self.last_sync_datetime = add_years(now(), -10)

	def unregister_from_hub(self):
		"""Unpublish, then delete transactions and user from there"""
		self.reset_publishing_settings()
		response_msg = send_hub_request('unregister')

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
		self.current_item_fields = json.dumps(self.base_fields_for_items)


	def set_publish_for_selling_items(self):
		"""Set `publish_in_hub`=1 for all Sales Items"""
		for item in frappe.get_all("Item", fields=["name"],
			filters={ "publish_in_hub": 0, "is_sales_item": 1}):
			frappe.db.set_value("Item", item.name, "publish_in_hub", 1)

	def publish_group(self):
		pass

	# get published items
	def bulk_update_hub_category(self):
		pass


### Helpers
def send_hub_request(method, data = [], now = True):
	hub = frappe.get_single("Hub Settings")
	response = requests.post(hub_url + "/api/method/hub.hub.api." + "call_method",
		data = {
			"access_token": hub.access_token,
			"method": method,
			"message": json.dumps(data)
		}
	)
	response.raise_for_status()
	return response.json().get("message")

### Sender terminal
def make_message_queue_table():
	pass

def store_as_job_message(method, data):
	# encrypt data and store both params in message queue
	pass

