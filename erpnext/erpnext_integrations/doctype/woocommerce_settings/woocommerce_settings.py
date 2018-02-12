# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests

from frappe import _
from frappe.utils.password import get_decrypted_password
from frappe.model.document import Document
from requests.auth import HTTPBasicAuth

class WoocommerceSettings(Document):
	def validate(self):
		self.validate_settings()
		self.create_webhooks()

	def validate_settings(self):
		if not self.secret:
			frappe.throw(_("Please Generate Secret"))
		if not self.woocommerce_server_url:
			pass

	def create_webhooks(self):
		api_consumer_secret = self.api_consumer_secret
		if self.coupon:
			coupon_created_webhook = self.generate_webhook_data("Coupon Created",
				"coupon.created",
				frappe.local.site + "/api/method/erpnext.erpnext_integrations.connectors.woocommerce_connection.coupon_created"
			)
			requests.post(self.woocommerce_server_url, auth=HTTPBasicAuth(self.api_consumer_key, api_consumer_secret), headers={
				"Content-Type":"application/json"
			}, data=coupon_created_webhook)
			coupon_updated_webhook = self.generate_webhook_data("Coupon Updated",
				"coupon.updated",
				frappe.local.site + "/api/method/erpnext.erpnext_integrations.connectors.woocommerce_connection.coupon_updated"
			)
			requests.post(self.woocommerce_server_url, auth=HTTPBasicAuth(self.api_consumer_key, api_consumer_secret), headers={
				"Content-Type":"application/json"
			}, data=coupon_updated_webhook)

	def generate_webhook_data(self, name, topic, delivery_url):
		return {
			"name": name,
			"topic": topic,
			"delivery_url": delivery_url,
			"secret": self.secret

		}

@frappe.whitelist()
def generate_secret():
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	woocommerce_settings.secret = frappe.generate_hash()
	woocommerce_settings.save()

@frappe.whitelist()
def force_delete():
	pass
