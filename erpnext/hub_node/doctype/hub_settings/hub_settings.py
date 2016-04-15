# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json
from frappe.model.document import Document
from frappe.utils import cint, expand_relative_urls
from frappe import _


class HubSettings(Document):
	hub_url = "http://localhost:8001"
	def validate(self):
		if cint(self.publish):
			if not self.name_token:
				self.register()
			else:
				self.update_seller_details()
			self.publish_selling_items()
		else:
			if self.name_token:
				self.unpublish()

	def publish_selling_items(self):
		"""Set `publish_in_hub`=1 for all Sales Items"""
		for item in frappe.get_all("Item", fields=["name"],
			filters={ "publish_in_hub": "0"}):
			frappe.db.set_value("Item", item.name, "publish_in_hub", 1)

	def register(self):
		"""Register at hub.erpnext.com, save `name_token` and `access_token`"""
		response = requests.post(self.hub_url + "/api/method/hub.hub.api.register", data=self.get_args())
		response.raise_for_status()
		response = response.json()
		self.name_token = response.get("message").get("name")
		self.access_token = response.get("message").get("access_token")

	def unpublish(self):
		"""Unpublish from hub.erpnext.com"""
		response = requests.post(self.hub_url + "/api/method/hub.hub.api.unpublish", data={
			"access_token": self.access_token
		})
		response.raise_for_status()

	def update_seller_details(self):
		"""Update details at hub.erpnext.com"""
		args = self.get_args()
		args["published"] = 1
		response = requests.post(self.hub_url + "/api/method/hub.hub.api.update_seller", data={
			"access_token": self.access_token,
			"args": json.dumps(args)
		})
		response.raise_for_status()

	def get_args(self):
		return {
			"seller_name": self.seller_name,
			"seller_country": self.seller_country,
			"seller_city": self.seller_city,
			"seller_email": self.seller_email,
			"seller_website": self.seller_website,
			"seller_description": self.seller_description
		}

	def sync(self, verbose=True):
		"""Sync items with hub.erpnext.com"""
		if not self.publish:
			if verbose:
				frappe.msgprint(_("Publish to sync items"))
			return

		items = frappe.db.get_all("Item",
			fields=["name", "item_name", "description", "image", "item_group"],
			filters={"publish_in_hub": 1, "synced_with_hub": 0})

		for item in items:
			item.item_code = item.name
			if item.image:
				item.image = expand_relative_urls(item.image)

		item_list = frappe.db.sql_list("select name from tabItem where publish_in_hub=1")

		if items:
			response = requests.post(self.hub_url + "/api/method/hub.hub.api.sync", data={
				"access_token": self.access_token,
				"items": json.dumps(items),
				"item_list": json.dumps(item_list)
			})
			response.raise_for_status()
			for item in items:
				frappe.db.set_value("Item", item.name, "synced_with_hub", 1)
			if verbose:
				frappe.msgprint(_("{0} Items synced".format(len(items))))
		else:
			if verbose:
				frappe.msgprint(_("Items already synced"))
