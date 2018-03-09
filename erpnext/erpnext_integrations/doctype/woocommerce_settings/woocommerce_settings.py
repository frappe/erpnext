# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, os

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

			if not frappe.get_value("Item Group",{"name": "WooCommerce Products"}):
				item_group = frappe.new_doc("Item Group")
				item_group.item_group_name = "WooCommerce Products"
				item_group.parent_item_group = "All Item Groups"
				item_group.save()


		elif not self.enable_sync:
			# delete
			names = ["Customer-woocommerce_id","Sales Order-woocommerce_id","Item-woocommerce_id","Address-woocommerce_id"]
			names_check_box = ["Customer-woocommerce_check","Sales Order-woocommerce_check","Item-woocommerce_check","Address-woocommerce_check"]
			email_names = ["Customer-woocommerce_email","Address-woocommerce_email"]
			for name in names:
				frappe.delete_doc("Custom Field",name)

			for name in names_check_box:
				frappe.delete_doc("Custom Field",name)

			for name in email_names:
				frappe.delete_doc("Custom Field",name)

			frappe.delete_doc("Item Group","WooCommerce Products")

				
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

def test_woocommerce_request():
	# Emulate Woocommerce Request
	headers = {
		"X-Wc-Webhook-Event":"created",
		"X-Wc-Webhook-Signature":"/AYKrScrgH3D4h7y2fphrltpZmpeA6pLxCDyOC5KH3o="
	}

	# Set Secret in Woocommerce Settings
	frappe.db.set_value("Woocommerce Settings", None, "secret", "ec434676aa1de0e502389f515c38f89f653119ab35e9117c7a79e576")
	frappe.db.commit()

	# Emulate Request Data
	data = """{"id":74,"parent_id":0,"number":"74","order_key":"wc_order_5aa1281c2dacb","created_via":"checkout","version":"3.3.3","status":"processing","currency":"INR","date_created":"2018-03-08T12:10:04","date_created_gmt":"2018-03-08T12:10:04","date_modified":"2018-03-08T12:10:04","date_modified_gmt":"2018-03-08T12:10:04","discount_total":"0.00","discount_tax":"0.00","shipping_total":"150.00","shipping_tax":"0.00","cart_tax":"0.00","total":"649.00","total_tax":"0.00","prices_include_tax":false,"customer_id":12,"customer_ip_address":"103.54.99.5","customer_user_agent":"mozilla\\/5.0 (x11; linux x86_64) applewebkit\\/537.36 (khtml, like gecko) chrome\\/64.0.3282.186 safari\\/537.36","customer_note":"","billing":{"first_name":"Tony","last_name":"Iron","company":"","address_1":"Mumbai","address_2":"","city":"Dadar","state":"MH","postcode":"123","country":"IN","email":"tony@gmail.com","phone":"123457890"},"shipping":{"first_name":"Tony","last_name":"Iron","company":"","address_1":"Mumbai","address_2":"","city":"Dadar","state":"MH","postcode":"123","country":"IN"},"payment_method":"cod","payment_method_title":"Cash on delivery","transaction_id":"","date_paid":null,"date_paid_gmt":null,"date_completed":null,"date_completed_gmt":null,"cart_hash":"8e76b020d5790066496f244860c4703f","meta_data":[],"line_items":[{"id":80,"name":"Infinity","product_id":56,"variation_id":0,"quantity":1,"tax_class":"","subtotal":"499.00","subtotal_tax":"0.00","total":"499.00","total_tax":"0.00","taxes":[],"meta_data":[],"sku":"","price":499}],"tax_lines":[],"shipping_lines":[{"id":81,"method_title":"Flat rate","method_id":"flat_rate:1","total":"150.00","total_tax":"0.00","taxes":[],"meta_data":[{"id":623,"key":"Items","value":"Marvel &times; 1"}]}],"fee_lines":[],"coupon_lines":[],"refunds":[]}"""

	# Build URL
	port = frappe.get_site_config().webserver_port or '8000'

	if os.environ.get('CI'):
		host = 'localhost'
	else:
		host = frappe.local.site

	url = "http://{site}:{port}/api/method/erpnext.erpnext_integrations.connectors.woocommerce_connection.order".format(site=host, port=port)

	requests.post(url=url, headers=headers, data=data)
