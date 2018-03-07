# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests

from frappe import _
from frappe.utils.password import get_decrypted_password
from frappe.model.document import Document
from six.moves.urllib.parse import urlparse

class WoocommerceSettings(Document):
	def validate(self):
		self.validate_settings()
		self.create_delete_custom_fields()
		self.create_webhook_url()

	def create_delete_custom_fields(self):
		if self.enable_sync:
			# create
			create_custom_field_id_and_check_status = False
			create_custom_field_email_check = False
			names = ["Customer-woocommerce_id","Sales Order-woocommerce_id","Item-woocommerce_id","Address-woocommerce_id"]
			names_check_box = ["Customer-woocommerce_check","Sales Order-woocommerce_check","Item-woocommerce_check","Address-woocommerce_check"]
			email_names = ["Customer-woocommerce_email","Address-woocommerce_email"]

			for i in zip(names,names_check_box):

				if not frappe.get_value("Custom Field",{"name":i[0]}) or not frappe.get_value("Custom Field",{"name":i[1]}):
					create_custom_field_id_and_check_status = True
					break;


			if create_custom_field_id_and_check_status:
				names = ["Customer","Sales Order","Item","Address"]
				for name in names:
					custom = frappe.new_doc("Custom Field")
					custom.dt = name
					custom.label = "woocommerce_id"
					custom.read_only = 1
					custom.save()

					custom = frappe.new_doc("Custom Field")
					custom.dt = name
					custom.label = "woocommerce_check"
					custom.fieldtype = "Check"
					custom.read_only = 1
					custom.save()

			for i in email_names:

				if not frappe.get_value("Custom Field",{"name":i}):
					create_custom_field_email_check = True
					break;

			if create_custom_field_email_check:
				names = ["Customer","Address"]
				for name in names:
					custom = frappe.new_doc("Custom Field")
					custom.dt = name
					custom.label = "woocommerce_email"
					custom.read_only = 1
					custom.save()

		elif not self.enable_sync:
			# delete
			names = ["Customer-woocommerce_id","Sales Order-woocommerce_id","Item-woocommerce_id","Address-woocommerce_id"]
			names_check_box = ["Customer-woocommerce_check","Sales Order-woocommerce_check","Item-woocommerce_check","Address-woocommerce_check"]
			email_names = ["Customer-woocommerce_email","Address-woocommerce_email"]
			for name in names:
				delete = frappe.delete_doc("Custom Field",name)

			for name in names_check_box:
				delete = frappe.delete_doc("Custom Field",name)

			for name in email_names:
				delete = frappe.delete_doc("Custom Field",name)

				
		frappe.db.commit()

	def validate_settings(self):
		if self.enable_sync:
			if not self.secret:
				self.set("secret", frappe.generate_hash())

			if not self.woocommerce_server_url:
				frappe.throw(_("Please enter Woocommerce Server URL"))

			if not self.api_consumer_key:
				frappe.throw(_("Please enter API Consumer Key"))

			if not self.api_consumer_secret:
				frappe.throw(_("Please enter API Consumer Secret"))

	def create_webhook_url(self):
	
		endpoint = "/api/method/erpnext.erpnext_integrations.connectors.woocommerce_connection.order"

		server_url = '{uri.scheme}://{uri.netloc}'.format(
			uri=urlparse(frappe.request.url)
		)

		delivery_url = server_url + endpoint
		self.endpoint = delivery_url

@frappe.whitelist()
def generate_secret():
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	woocommerce_settings.secret = frappe.generate_hash()
	woocommerce_settings.save()

@frappe.whitelist()
def force_delete():
	pass


