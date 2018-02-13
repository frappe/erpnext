# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests

from frappe import _
from frappe.utils.password import get_decrypted_password
from frappe.model.document import Document
from woocommerce import API
from six.moves.urllib.parse import urlparse

class WoocommerceSettings(Document):
	def validate(self):
		self.validate_settings()

	def validate_settings(self):
		if not self.secret:
			self.set("secret", frappe.generate_hash())

		if not self.woocommerce_server_url:
			frappe.throw(_("Please enter Woocommerce Server URL"))

		if not self.api_consumer_key:
			frappe.throw(_("Please enter API Consumer Key"))

		if not self.api_consumer_secret:
			frappe.throw(_("Please enter API Consumer Secret"))

	def create_webhooks(self):
		self.create_coupon_webhooks()

	def create_coupon_webhooks(self):
		# Coupon Created
		create_coupon_data = self.generate_webhook_data(
			name="ERPNext Coupon Created",
			topic="coupon.created",
			endpoint= "/api/method/erpnext.erpnext_integrations.connectors.woocommerce_connection.create_coupon"
		)
		self.woocommerce_request("webhooks", create_coupon_data)

		# Coupon Updated
		update_coupon_data = self.generate_webhook_data(
			name="ERPNext Coupon Updated",
			topic="coupon.updated",
			endpoint= "/api/method/erpnext.erpnext_integrations.connectors.woocommerce_connection.update_coupon"
		)
		self.woocommerce_request("webhooks", update_coupon_data)

		# Coupon Deleted
		delete_coupon_data = self.generate_webhook_data(
			name="ERPNext Coupon Deleted",
			topic="coupon.deleted",
			endpoint= "/api/method/erpnext.erpnext_integrations.connectors.woocommerce_connection.delete_coupon"
		)
		self.woocommerce_request("webhooks", delete_coupon_data)

		# Coupon Restored
		delete_coupon_data = self.generate_webhook_data(
			name="ERPNext Coupon Restored",
			topic="coupon.restored",
			endpoint= "/api/method/erpnext.erpnext_integrations.connectors.woocommerce_connection.restore_coupon"
		)
		self.woocommerce_request("webhooks", delete_coupon_data)

	def generate_webhook_data(self, name, topic, endpoint):
		server_url = '{uri.scheme}://{uri.netloc}'.format(
			uri=urlparse(frappe.request.url)
		)
		return {
			'name': name,
			'delivery_url': server_url + endpoint,
			'secret': self.secret,
			'topic': topic
		}

	def woocommerce_request(self, endpoint, data):
		wcapi = API(
			url = self.woocommerce_server_url,
			consumer_key = self.api_consumer_key,
			consumer_secret = self.api_consumer_secret,
			wp_api = True,
			version = "wc/v2"
		)
		wcapi.post(endpoint, data)

@frappe.whitelist()
def generate_secret():
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	woocommerce_settings.secret = frappe.generate_hash()
	woocommerce_settings.save()

@frappe.whitelist()
def force_delete():
	pass
