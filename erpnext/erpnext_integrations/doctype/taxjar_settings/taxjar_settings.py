# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json
import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model.document import Document
from frappe.permissions import add_permission, update_permission_property

from erpnext.erpnext_integrations.taxjar_integration import get_client


class TaxJarSettings(Document):
	def on_update(self):
		TAXJAR_CREATE_TRANSACTIONS = self.taxjar_create_transactions
		TAXJAR_CALCULATE_TAX = self.taxjar_calculate_tax
		TAXJAR_SANDBOX_MODE = self.is_sandbox

		fields_already_exist = frappe.db.exists(
			"Custom Field",
			{"dt": ("in", ["Item", "Sales Invoice Item"]), "fieldname": "product_tax_category"},
		)
		fields_hidden = frappe.get_value(
			"Custom Field", {"dt": ("in", ["Sales Invoice Item"])}, "hidden"
		)

		if TAXJAR_CREATE_TRANSACTIONS or TAXJAR_CALCULATE_TAX or TAXJAR_SANDBOX_MODE:
			if not fields_already_exist:
				add_product_tax_categories()
				make_custom_fields()
				add_permissions()
				frappe.enqueue("erpnext.regional.united_states.setup.add_product_tax_categories", now=False)

			elif fields_already_exist and fields_hidden:
				toggle_tax_category_fields(hidden="0")

		elif fields_already_exist:
			toggle_tax_category_fields(hidden="1")

	def validate(self):
		self.calculate_taxes_validation_for_create_transactions()

	@frappe.whitelist()
	def update_nexus_list(self):
		client = get_client()
		nexus = client.nexus_regions()

		new_nexus_list = [frappe._dict(address) for address in nexus]

		self.set("nexus", [])
		self.set("nexus", new_nexus_list)
		self.save()

	def calculate_taxes_validation_for_create_transactions(self):
		if not self.taxjar_calculate_tax and (self.taxjar_create_transactions or self.is_sandbox):
			frappe.throw(
				frappe._(
					"Before enabling <b>Create Transaction</b> or <b>Sandbox Mode</b>, you need to check the <b>Enable Tax Calculation</b> box"
				)
			)


def toggle_tax_category_fields(hidden):
	frappe.set_value(
		"Custom Field",
		{"dt": "Sales Invoice Item", "fieldname": "product_tax_category"},
		"hidden",
		hidden,
	)
	frappe.set_value(
		"Custom Field", {"dt": "Item", "fieldname": "product_tax_category"}, "hidden", hidden
	)


def add_product_tax_categories():
	with open(os.path.join(os.path.dirname(__file__), "product_tax_category_data.json"), "r") as f:
		tax_categories = json.loads(f.read())
	create_tax_categories(tax_categories["categories"])


def create_tax_categories(data):
	for d in data:
		if not frappe.db.exists("Product Tax Category", {"product_tax_code": d.get("product_tax_code")}):
			tax_category = frappe.new_doc("Product Tax Category")
			tax_category.description = d.get("description")
			tax_category.product_tax_code = d.get("product_tax_code")
			tax_category.category_name = d.get("name")
			tax_category.db_insert()


def make_custom_fields(update=True):
	custom_fields = {
		"Sales Invoice Item": [
			dict(
				fieldname="product_tax_category",
				fieldtype="Link",
				insert_after="description",
				options="Product Tax Category",
				label="Product Tax Category",
				fetch_from="item_code.product_tax_category",
			),
			dict(
				fieldname="tax_collectable",
				fieldtype="Currency",
				insert_after="net_amount",
				label="Tax Collectable",
				read_only=1,
				options="currency",
			),
			dict(
				fieldname="taxable_amount",
				fieldtype="Currency",
				insert_after="tax_collectable",
				label="Taxable Amount",
				read_only=1,
				options="currency",
			),
		],
		"Item": [
			dict(
				fieldname="product_tax_category",
				fieldtype="Link",
				insert_after="item_group",
				options="Product Tax Category",
				label="Product Tax Category",
			)
		],
	}
	create_custom_fields(custom_fields, update=update)


def add_permissions():
	doctype = "Product Tax Category"
	for role in (
		"Accounts Manager",
		"Accounts User",
		"System Manager",
		"Item Manager",
		"Stock Manager",
	):
		add_permission(doctype, role, 0)
		update_permission_property(doctype, role, 0, "write", 1)
		update_permission_property(doctype, role, 0, "create", 1)
