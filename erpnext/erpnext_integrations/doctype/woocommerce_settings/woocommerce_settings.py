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
		# self.validate_settings()
		self.create_webhooks()

	def validate_settings(self):
		if not self.secret:
			frappe.throw(_("Please Generate Secret"))
		if not self.woocommerce_server_url:
			pass

	def create_webhooks(self):
		api_consumer_secret = self.api_consumer_secret
		if self.coupon:
			# coupon_created_webhook = self.generate_webhook_data("Coupon Created",
			# 	"coupon.created",
			# 	frappe.local.site + "/api/method/erpnext.erpnext_integrations.connectors.woocommerce_connection.coupon_created"
			# )
			# requests.post(self.woocommerce_server_url, auth=HTTPBasicAuth(self.api_consumer_key, api_consumer_secret), headers={
			# 	"Content-Type":"application/json"
			# }, data=coupon_created_webhook)
			# requests.post(self.woocommerce_server_url+"/wp-json/wc/v2/webhooks", auth=requests.auth.HTTPBasicAuth(self.api_consumer_key, self.api_consumer_secret), data=data).json()
			server_url = frappe.local.site

			coupon_updated_webhook = self.generate_webhook_data(
				name="Coupon Updated",
				topic="coupon.updated",
				delivery_url= "https://"+ frappe.local.site + "/api/method/erpnext.erpnext_integrations.connectors.woocommerce_connection.coupon_updated",
				event="coupon",
				hooks=['woocommerce_process_shop_coupon_meta', 'woocommerce_new_coupon'],
				resource='coupon'
			)
			r = requests.post(
				url=self.woocommerce_server_url+"/wp-json/wc/v2/webhooks",
				auth=HTTPBasicAuth(self.api_consumer_key, api_consumer_secret),
				data=coupon_updated_webhook
			)

	def generate_webhook_data(self, name, topic, delivery_url, event, hooks, resource):
		return {
			'name': name,
			'delivery_url': delivery_url,
			'event': event,
			'hooks': hooks,
			'resource': resource,
			'secret': self.secret,
			'status': 'active',
			'topic': topic
		}

@frappe.whitelist()
def generate_secret():
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	woocommerce_settings.secret = frappe.generate_hash()
	woocommerce_settings.save()

@frappe.whitelist()
def force_delete():
	pass
