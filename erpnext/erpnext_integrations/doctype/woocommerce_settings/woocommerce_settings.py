# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model.document import Document
from frappe.utils.nestedset import get_root_of


class WoocommerceSettings(Document):
	def validate(self):
		self.validate_settings()
		self.create_delete_custom_fields()
		self.create_webhook_url()

	def create_delete_custom_fields(self):
		if self.enable_sync:
			create_custom_fields(
				{
					("Customer", "Sales Order", "Item", "Address"): dict(
						fieldname="woocommerce_id",
						label="Woocommerce ID",
						fieldtype="Data",
						read_only=1,
						print_hide=1,
					),
					("Customer", "Address"): dict(
						fieldname="woocommerce_email",
						label="Woocommerce Email",
						fieldtype="Data",
						read_only=1,
						print_hide=1,
					),
				}
			)

			if not frappe.get_value("Item Group", {"name": _("WooCommerce Products")}):
				item_group = frappe.new_doc("Item Group")
				item_group.item_group_name = _("WooCommerce Products")
				item_group.parent_item_group = get_root_of("Item Group")
				item_group.insert()

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

		try:
			url = frappe.request.url
		except RuntimeError:
			# for CI Test to work
			url = "http://localhost:8000"

		server_url = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(url))

		delivery_url = server_url + endpoint
		self.endpoint = delivery_url


@frappe.whitelist()
def generate_secret():
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	woocommerce_settings.secret = frappe.generate_hash()
	woocommerce_settings.save()


@frappe.whitelist()
def get_series():
	return {
		"sales_order_series": frappe.get_meta("Sales Order").get_options("naming_series") or "SO-WOO-",
	}
