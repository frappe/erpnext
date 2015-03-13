# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe
from erpnext.shopping_cart import get_quotation, set_item_in_cart

class TestShoppingCart(unittest.TestCase):
	"""
		Note:
		Shopping Cart == Quotation
	"""
	def setUp(self):
		frappe.set_user("Administrator")
		self.enable_shopping_cart()

	def tearDown(self):
		frappe.set_user("Administrator")
		self.disable_shopping_cart()

	def test_get_cart_new_user(self):
		self.login_as_new_user()

		# test if lead is created and quotation with new lead is fetched
		quotation = get_quotation()
		self.assertEquals(quotation.quotation_to, "Lead")
		self.assertEquals(frappe.db.get_value("Lead", quotation.lead, "email_id"), "test_cart_user@example.com")
		self.assertEquals(quotation.customer, None)
		self.assertEquals(quotation.contact_email, frappe.session.user)

		return quotation

	def test_get_cart_lead(self):
		self.login_as_lead()

		# test if quotation with lead is fetched
		quotation = get_quotation()
		self.assertEquals(quotation.quotation_to, "Lead")
		self.assertEquals(quotation.lead, frappe.db.get_value("Lead", {"email_id": "test_cart_lead@example.com"}))
		self.assertEquals(quotation.customer, None)
		self.assertEquals(quotation.contact_email, frappe.session.user)

		return quotation

	def test_get_cart_customer(self):
		self.login_as_customer()

		# test if quotation with customer is fetched
		quotation = get_quotation()
		self.assertEquals(quotation.quotation_to, "Customer")
		self.assertEquals(quotation.customer, "_Test Customer")
		self.assertEquals(quotation.lead, None)
		self.assertEquals(quotation.contact_email, frappe.session.user)

		return quotation

	def test_add_to_cart(self):
		self.login_as_lead()

		# remove from cart
		self.remove_all_items_from_cart()
		
		# add first item
		set_item_in_cart("_Test Item", 1)
		quotation = self.test_get_cart_lead()
		self.assertEquals(quotation.get("items")[0].item_code, "_Test Item")
		self.assertEquals(quotation.get("items")[0].qty, 1)
		self.assertEquals(quotation.get("items")[0].amount, 10)

		# add second item
		set_item_in_cart("_Test Item 2", 1)
		quotation = self.test_get_cart_lead()
		self.assertEquals(quotation.get("items")[1].item_code, "_Test Item 2")
		self.assertEquals(quotation.get("items")[1].qty, 1)
		self.assertEquals(quotation.get("items")[1].amount, 20)

		self.assertEquals(len(quotation.get("items")), 2)

	def test_update_cart(self):
		# first, add to cart
		self.test_add_to_cart()

		# update first item
		set_item_in_cart("_Test Item", 5)
		quotation = self.test_get_cart_lead()
		self.assertEquals(quotation.get("items")[0].item_code, "_Test Item")
		self.assertEquals(quotation.get("items")[0].qty, 5)
		self.assertEquals(quotation.get("items")[0].amount, 50)
		self.assertEquals(quotation.net_total, 70)
		self.assertEquals(len(quotation.get("items")), 2)

	def test_remove_from_cart(self):
		# first, add to cart
		self.test_add_to_cart()

		# remove first item
		set_item_in_cart("_Test Item", 0)
		quotation = self.test_get_cart_lead()
		self.assertEquals(quotation.get("items")[0].item_code, "_Test Item 2")
		self.assertEquals(quotation.get("items")[0].qty, 1)
		self.assertEquals(quotation.get("items")[0].amount, 20)
		self.assertEquals(quotation.net_total, 20)
		self.assertEquals(len(quotation.get("items")), 1)

		# remove second item
		set_item_in_cart("_Test Item 2", 0)
		quotation = self.test_get_cart_lead()
		self.assertEquals(quotation.net_total, 0)
		self.assertEquals(len(quotation.get("items")), 0)

	def test_set_billing_address(self):
		return

		# first, add to cart
		self.test_add_to_cart()

		quotation = self.test_get_cart_lead()
		default_address = frappe.get_doc("Address", {"lead": quotation.lead, "is_primary_address": 1})
		self.assertEquals("customer_address", default_address.name)

	def test_set_shipping_address(self):
		# first, add to cart
		self.test_add_to_cart()



	def test_shipping_rule(self):
		self.test_set_shipping_address()

		# check if shipping rule changed
		pass

	def test_price_list(self):
		self.test_set_billing_address()

		# check if price changed
		pass

	def test_place_order(self):
		pass

	# helper functions
	def enable_shopping_cart(self):
		settings = frappe.get_doc("Shopping Cart Settings", "Shopping Cart Settings")

		if settings.get("price_lists"):
			settings.enabled = 1
		else:
			settings.update({
				"enabled": 1,
				"company": "_Test Company",
				"default_territory": "_Test Territory Rest Of The World",
				"default_customer_group": "_Test Customer Group",
				"quotation_series": "_T-Quotation-"
			})
			settings.set("price_lists", [
				# price lists
				{"doctype": "Shopping Cart Price List", "parentfield": "price_lists",
					"selling_price_list": "_Test Price List India"},
				{"doctype": "Shopping Cart Price List", "parentfield": "price_lists",
					"selling_price_list": "_Test Price List Rest of the World"}
			])
			settings.set("sales_taxes_and_charges_masters", [
				# tax masters
				{"doctype": "Shopping Cart Taxes and Charges Master", "parentfield": "sales_taxes_and_charges_masters",
					"sales_taxes_and_charges_master": "_Test India Tax Master"},
				{"doctype": "Shopping Cart Taxes and Charges Master", "parentfield": "sales_taxes_and_charges_masters",
					"sales_taxes_and_charges_master": "_Test Sales Taxes and Charges Master - Rest of the World"},
			])
			settings.set("shipping_rules", {"doctype": "Shopping Cart Shipping Rule", "parentfield": "shipping_rules",
					"shipping_rule": "_Test Shipping Rule - India"})

		settings.save()
		frappe.local.shopping_cart_settings = None

	def disable_shopping_cart(self):
		settings = frappe.get_doc("Shopping Cart Settings", "Shopping Cart Settings")
		settings.enabled = 0
		settings.save()
		frappe.local.shopping_cart_settings = None

	def login_as_new_user(self):
		frappe.set_user("test_cart_user@example.com")

	def login_as_lead(self):
		self.create_lead()
		frappe.set_user("test_cart_lead@example.com")

	def login_as_customer(self):
		frappe.set_user("test_contact_customer@example.com")

	def create_lead(self):
		if frappe.db.get_value("Lead", {"email_id": "test_cart_lead@example.com"}):
			return

		lead = frappe.get_doc({
			"doctype": "Lead",
			"email_id": "test_cart_lead@example.com",
			"lead_name": "_Test Website Lead",
			"status": "Open",
			"territory": "_Test Territory Rest Of The World"
		})
		lead.insert(ignore_permissions=True)

		frappe.get_doc({
			"doctype": "Address",
			"address_line1": "_Test Address Line 1",
			"address_title": "_Test Cart Lead Address",
			"address_type": "Office",
			"city": "_Test City",
			"country": "United States",
			"lead": lead.name,
			"lead_name": "_Test Website Lead",
			"is_primary_address": 1,
			"phone": "+91 0000000000"
		}).insert(ignore_permissions=True)

		frappe.get_doc({
			"doctype": "Address",
			"address_line1": "_Test Address Line 1",
			"address_title": "_Test Cart Lead Address",
			"address_type": "Personal",
			"city": "_Test City",
			"country": "India",
			"lead": lead.name,
			"lead_name": "_Test Website Lead",
			"phone": "+91 0000000000"
		}).insert(ignore_permissions=True)
		
	def remove_all_items_from_cart(self):
		quotation = get_quotation()
		quotation.set("items", [])
		quotation.save(ignore_permissions=True)


test_dependencies = ["Sales Taxes and Charges Master", "Price List", "Item Price", "Shipping Rule", "Currency Exchange",
	"Customer Group", "Lead", "Customer", "Contact", "Address", "Item"]
