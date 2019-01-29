# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_request_session
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from erpnext.erpnext_integrations.utils import get_webhook_address
from erpnext.erpnext_integrations.doctype.shopify_log.shopify_log import make_shopify_log

class ShopifySettings(Document):
	def validate(self):
		if self.enable_shopify == 1:
			setup_custom_fields()
			self.validate_access_credentials()
			self.register_webhooks()
		else:
			self.unregister_webhooks()

		self.validate_app_type()

	def validate_access_credentials(self):
		if self.app_type == "Private":
			if not (self.get_password(raise_exception=False) and self.api_key and self.shopify_url):
				frappe.msgprint(_("Missing value for Password, API Key or Shopify URL"), raise_exception=frappe.ValidationError)

		else:
			if not (self.access_token and self.shopify_url):
				frappe.msgprint(_("Access token or Shopify URL missing"), raise_exception=frappe.ValidationError)

	def validate_app_type(self):
		if self.app_type == "Public":
			frappe.throw(_("Support for public app is deprecated. Please setup private app, for more details refer user manual"))

	def register_webhooks(self):
		webhooks = ["orders/create", "orders/paid", "orders/fulfilled"]

		url = get_shopify_url('admin/webhooks.json', self)
		created_webhooks = [d.method for d in self.webhooks]

		for method in webhooks:
			if method in created_webhooks:
				continue

			session = get_request_session()
			try:
				d = session.post(url, data=json.dumps({
					"webhook": {
						"topic": method,
						"address": get_webhook_address(connector_name='shopify_connection', method='store_request_data'),
						"format": "json"
						}
					}), headers=get_header(self))
				d.raise_for_status()
				self.update_webhook_table(method, d.json())
			except Exception as e:
				make_shopify_log(status="Warning", message=e.message, exception=False)

	def unregister_webhooks(self):
		session = get_request_session()
		deleted_webhooks = []

		for d in self.webhooks:
			url = get_shopify_url('admin/webhooks/{0}.json'.format(d.webhook_id), self)
			try:
				res = session.delete(url, headers=get_header(self))
				res.raise_for_status()
				deleted_webhooks.append(d)
			except Exception as e:
				frappe.log_error(message=frappe.get_traceback(), title=e.message[:140])

		for d in deleted_webhooks:
			self.remove(d)

	def update_webhook_table(self, method, res):
		self.append("webhooks", {
			"webhook_id": res['webhook']['id'],
			"method": method
		})

def get_shopify_url(path, settings):
	if settings.app_type == "Private":
		return 'https://{}:{}@{}/{}'.format(settings.api_key, settings.get_password('password'), settings.shopify_url, path)
	else:
		return 'https://{}/{}'.format(settings.shopify_url, path)

def get_header(settings):
	header = {'Content-Type': 'application/json'}

	if settings.app_type == "Private":
		return header
	else:
		header["X-Shopify-Access-Token"] = settings.access_token
		return header

@frappe.whitelist()
def get_series():
	return {
		"sales_order_series" : frappe.get_meta("Sales Order").get_options("naming_series") or "SO-Shopify-",
		"sales_invoice_series" : frappe.get_meta("Sales Invoice").get_options("naming_series")  or "SI-Shopify-",
		"delivery_note_series" : frappe.get_meta("Delivery Note").get_options("naming_series")  or "DN-Shopify-"
	}

def setup_custom_fields():
	custom_fields = {
		"Customer": [dict(fieldname='shopify_customer_id', label='Shopify Customer Id',
			fieldtype='Data', insert_after='series', read_only=1, print_hide=1)],
		"Address": [dict(fieldname='shopify_address_id', label='Shopify Address Id',
			fieldtype='Data', insert_after='fax', read_only=1, print_hide=1)],
		"Item": [
			dict(fieldname='shopify_variant_id', label='Shopify Variant Id',
				fieldtype='Data', insert_after='item_code', read_only=1, print_hide=1),
			dict(fieldname='shopify_product_id', label='Shopify Product Id',
				fieldtype='Data', insert_after='item_code', read_only=1, print_hide=1),
			dict(fieldname='shopify_description', label='Shopify Description',
				fieldtype='Text Editor', insert_after='description', read_only=1, print_hide=1)
		],
		"Sales Order": [dict(fieldname='shopify_order_id', label='Shopify Order Id',
			fieldtype='Data', insert_after='title', read_only=1, print_hide=1)],
		"Delivery Note":[
			dict(fieldname='shopify_order_id', label='Shopify Order Id',
				fieldtype='Data', insert_after='title', read_only=1, print_hide=1),
			dict(fieldname='shopify_fulfillment_id', label='Shopify Fulfillment Id',
				fieldtype='Data', insert_after='title', read_only=1, print_hide=1)
		],
		"Sales Invoice": [dict(fieldname='shopify_order_id', label='Shopify Order Id',
			fieldtype='Data', insert_after='title', read_only=1, print_hide=1)]
	}

	create_custom_fields(custom_fields)

