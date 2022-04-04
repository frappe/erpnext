# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe
from frappe.tests.utils import change_settings
from frappe.utils import add_months, cint, nowdate

from erpnext.accounts.doctype.tax_rule.tax_rule import ConflictingTaxRule
from erpnext.e_commerce.doctype.website_item.website_item import make_website_item
from erpnext.e_commerce.shopping_cart.cart import (
	_get_cart_quotation,
	get_cart_quotation,
	get_party,
	request_for_quotation,
	update_cart,
)
from erpnext.tests.utils import create_test_contact_and_address


class TestShoppingCart(unittest.TestCase):
	"""
	Note:
	Shopping Cart == Quotation
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		create_test_contact_and_address()
		self.enable_shopping_cart()
		if not frappe.db.exists("Website Item", {"item_code": "_Test Item"}):
			make_website_item(frappe.get_cached_doc("Item", "_Test Item"))

		if not frappe.db.exists("Website Item", {"item_code": "_Test Item 2"}):
			make_website_item(frappe.get_cached_doc("Item", "_Test Item 2"))

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")
		self.disable_shopping_cart()

	@classmethod
	def tearDownClass(cls):
		frappe.db.sql("delete from `tabTax Rule`")

	def test_get_cart_new_user(self):
		self.login_as_new_user()

		# test if lead is created and quotation with new lead is fetched
		quotation = _get_cart_quotation()
		self.assertEqual(quotation.quotation_to, "Customer")
		self.assertEqual(
			quotation.contact_person,
			frappe.db.get_value("Contact", dict(email_id="test_cart_user@example.com")),
		)
		self.assertEqual(quotation.contact_email, frappe.session.user)

		return quotation

	def test_get_cart_customer(self):
		def validate_quotation():
			# test if quotation with customer is fetched
			quotation = _get_cart_quotation()
			self.assertEqual(quotation.quotation_to, "Customer")
			self.assertEqual(quotation.party_name, "_Test Customer")
			self.assertEqual(quotation.contact_email, frappe.session.user)
			return quotation

		self.login_as_customer(
			"test_contact_two_customer@example.com", "_Test Contact 2 For _Test Customer"
		)
		validate_quotation()

		self.login_as_customer()
		quotation = validate_quotation()

		return quotation

	def test_add_to_cart(self):
		self.login_as_customer()

		# clear existing quotations
		self.clear_existing_quotations()

		# add first item
		update_cart("_Test Item", 1)

		quotation = self.test_get_cart_customer()

		self.assertEqual(quotation.get("items")[0].item_code, "_Test Item")
		self.assertEqual(quotation.get("items")[0].qty, 1)
		self.assertEqual(quotation.get("items")[0].amount, 10)

		# add second item
		update_cart("_Test Item 2", 1)
		quotation = self.test_get_cart_customer()
		self.assertEqual(quotation.get("items")[1].item_code, "_Test Item 2")
		self.assertEqual(quotation.get("items")[1].qty, 1)
		self.assertEqual(quotation.get("items")[1].amount, 20)

		self.assertEqual(len(quotation.get("items")), 2)

	def test_update_cart(self):
		# first, add to cart
		self.test_add_to_cart()

		# update first item
		update_cart("_Test Item", 5)
		quotation = self.test_get_cart_customer()
		self.assertEqual(quotation.get("items")[0].item_code, "_Test Item")
		self.assertEqual(quotation.get("items")[0].qty, 5)
		self.assertEqual(quotation.get("items")[0].amount, 50)
		self.assertEqual(quotation.net_total, 70)
		self.assertEqual(len(quotation.get("items")), 2)

	def test_remove_from_cart(self):
		# first, add to cart
		self.test_add_to_cart()

		# remove first item
		update_cart("_Test Item", 0)
		quotation = self.test_get_cart_customer()

		self.assertEqual(quotation.get("items")[0].item_code, "_Test Item 2")
		self.assertEqual(quotation.get("items")[0].qty, 1)
		self.assertEqual(quotation.get("items")[0].amount, 20)
		self.assertEqual(quotation.net_total, 20)
		self.assertEqual(len(quotation.get("items")), 1)

	def test_tax_rule(self):
		self.create_tax_rule()
		self.login_as_customer()
		quotation = self.create_quotation()

		from erpnext.accounts.party import set_taxes

		tax_rule_master = set_taxes(
			quotation.party_name,
			"Customer",
			quotation.transaction_date,
			quotation.company,
			customer_group=None,
			supplier_group=None,
			tax_category=quotation.tax_category,
			billing_address=quotation.customer_address,
			shipping_address=quotation.shipping_address_name,
			use_for_shopping_cart=1,
		)

		self.assertEqual(quotation.taxes_and_charges, tax_rule_master)
		self.assertEqual(quotation.total_taxes_and_charges, 1000.0)

		self.remove_test_quotation(quotation)

	@change_settings(
		"E Commerce Settings",
		{
			"company": "_Test Company",
			"enabled": 1,
			"default_customer_group": "_Test Customer Group",
			"price_list": "_Test Price List India",
			"show_price": 1,
		},
	)
	def test_add_item_variant_without_web_item_to_cart(self):
		"Test adding Variants having no Website Items in cart via Template Web Item."
		from erpnext.controllers.item_variant import create_variant
		from erpnext.e_commerce.doctype.website_item.website_item import make_website_item
		from erpnext.stock.doctype.item.test_item import make_item

		template_item = make_item(
			"Test-Tshirt-Temp",
			{
				"has_variant": 1,
				"variant_based_on": "Item Attribute",
				"attributes": [{"attribute": "Test Size"}, {"attribute": "Test Colour"}],
			},
		)
		variant = create_variant("Test-Tshirt-Temp", {"Test Size": "Small", "Test Colour": "Red"})
		variant.save()
		make_website_item(template_item)  # publish template not variant

		update_cart("Test-Tshirt-Temp-S-R", 1)

		cart = get_cart_quotation()  # test if cart page gets data without errors
		doc = cart.get("doc")

		self.assertEqual(doc.get("items")[0].item_name, "Test-Tshirt-Temp-S-R")

		# test if items are rendered without error
		frappe.render_template("templates/includes/cart/cart_items.html", cart)

	@change_settings("E Commerce Settings", {"save_quotations_as_draft": 1})
	def test_cart_without_checkout_and_draft_quotation(self):
		"Test impact of 'save_quotations_as_draft' checkbox."
		frappe.local.shopping_cart_settings = None

		# add item to cart
		update_cart("_Test Item", 1)
		quote_name = request_for_quotation()  # Request for Quote
		quote_doctstatus = cint(frappe.db.get_value("Quotation", quote_name, "docstatus"))

		self.assertEqual(quote_doctstatus, 0)

		frappe.db.set_value("E Commerce Settings", None, "save_quotations_as_draft", 0)
		frappe.local.shopping_cart_settings = None
		update_cart("_Test Item", 1)
		quote_name = request_for_quotation()  # Request for Quote
		quote_doctstatus = cint(frappe.db.get_value("Quotation", quote_name, "docstatus"))

		self.assertEqual(quote_doctstatus, 1)

	def create_tax_rule(self):
		tax_rule = frappe.get_test_records("Tax Rule")[0]
		try:
			frappe.get_doc(tax_rule).insert()
		except (frappe.DuplicateEntryError, ConflictingTaxRule):
			pass

	def create_quotation(self):
		quotation = frappe.new_doc("Quotation")

		values = {
			"doctype": "Quotation",
			"quotation_to": "Customer",
			"order_type": "Shopping Cart",
			"party_name": get_party(frappe.session.user).name,
			"docstatus": 0,
			"contact_email": frappe.session.user,
			"selling_price_list": "_Test Price List Rest of the World",
			"currency": "USD",
			"taxes_and_charges": "_Test Tax 1 - _TC",
			"conversion_rate": 1,
			"transaction_date": nowdate(),
			"valid_till": add_months(nowdate(), 1),
			"items": [{"item_code": "_Test Item", "qty": 1}],
			"taxes": frappe.get_doc("Sales Taxes and Charges Template", "_Test Tax 1 - _TC").taxes,
			"company": "_Test Company",
		}

		quotation.update(values)

		quotation.insert(ignore_permissions=True)

		return quotation

	def remove_test_quotation(self, quotation):
		frappe.set_user("Administrator")
		quotation.delete()

	# helper functions
	def enable_shopping_cart(self):
		settings = frappe.get_doc("E Commerce Settings", "E Commerce Settings")

		settings.update(
			{
				"enabled": 1,
				"company": "_Test Company",
				"default_customer_group": "_Test Customer Group",
				"quotation_series": "_T-Quotation-",
				"price_list": "_Test Price List India",
			}
		)

		# insert item price
		if not frappe.db.get_value(
			"Item Price", {"price_list": "_Test Price List India", "item_code": "_Test Item"}
		):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"price_list": "_Test Price List India",
					"item_code": "_Test Item",
					"price_list_rate": 10,
				}
			).insert()
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"price_list": "_Test Price List India",
					"item_code": "_Test Item 2",
					"price_list_rate": 20,
				}
			).insert()

		settings.save()
		frappe.local.shopping_cart_settings = None

	def disable_shopping_cart(self):
		settings = frappe.get_doc("E Commerce Settings", "E Commerce Settings")
		settings.enabled = 0
		settings.save()
		frappe.local.shopping_cart_settings = None

	def login_as_new_user(self):
		self.create_user_if_not_exists("test_cart_user@example.com")
		frappe.set_user("test_cart_user@example.com")

	def login_as_customer(
		self, email="test_contact_customer@example.com", name="_Test Contact For _Test Customer"
	):
		self.create_user_if_not_exists(email, name)
		frappe.set_user(email)

	def clear_existing_quotations(self):
		quotations = frappe.get_all(
			"Quotation",
			filters={"party_name": get_party().name, "order_type": "Shopping Cart", "docstatus": 0},
			order_by="modified desc",
			pluck="name",
		)

		for quotation in quotations:
			frappe.delete_doc("Quotation", quotation, ignore_permissions=True, force=True)

	def create_user_if_not_exists(self, email, first_name=None):
		if frappe.db.exists("User", email):
			return

		frappe.get_doc(
			{
				"doctype": "User",
				"user_type": "Website User",
				"email": email,
				"send_welcome_email": 0,
				"first_name": first_name or email.split("@")[0],
			}
		).insert(ignore_permissions=True)


test_dependencies = [
	"Sales Taxes and Charges Template",
	"Price List",
	"Item Price",
	"Shipping Rule",
	"Currency Exchange",
	"Customer Group",
	"Lead",
	"Customer",
	"Contact",
	"Address",
	"Item",
	"Tax Rule",
]
