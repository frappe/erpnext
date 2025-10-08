# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from datetime import date, timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, flt, get_time, now

from erpnext.accounts.doctype.account.test_account import make_company
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_address
from erpnext.stock.doctype.delivery_note.delivery_note import make_shipment
from erpnext.stock.doctype.item.test_item import get_hsn


class TestShipment(FrappeTestCase):
	def setUp(self):
		self.company = "_Test Indian Registered Company"
		if not frappe.db.exists("Company", self.company):
			make_company(self.company)

		self.args1 = {
			"address_title": "Test Address1",
			"address_type": "Permanent",
			"address_line1": "Test Address1",
			"is_primary_address": 1,
			"state": "Karnataka",
			"country": "India",
			"pincode": "581115",
			"company": self.company,
			"is_your_company_address": 1,
			"doctype": "Company",
			"docname": self.company,
		}

		self.args2 = {
			"address_title": "Test Address2",
			"address_type": "Permanent",
			"address_line1": "Test Address1",
			"is_primary_address": 1,
			"state": "Karnataka",
			"country": "India",
			"pincode": "581115",
			"company": self.company,
			"is_your_company_address": 1,
			"doctype": "Company",
			"docname": self.company,
		}

	def test_shipment_from_delivery_note(self):
		delivery_note = create_test_delivery_note()
		delivery_note.submit()
		shipment = create_test_shipment([delivery_note])
		shipment.submit()
		second_shipment = make_shipment(delivery_note.name)
		self.assertEqual(second_shipment.value_of_goods, delivery_note.grand_total)
		self.assertEqual(len(second_shipment.shipment_delivery_note), 1)
		self.assertEqual(second_shipment.shipment_delivery_note[0].delivery_note, delivery_note.name)

	def tearDown(self):
		frappe.db.rollback()

	# codecov
	def test_validate_weight_TC_SCK_353(self):
		address1 = create_address(**self.args1)

		address2 = create_address(**self.args2)

		shipment = frappe.get_doc(
			{
				"doctype": "Shipment",
				"pickup_from_type": "Company",
				"pickup_address_name": address1.name,
				"pickup_contact_person": "Administrator",
				"delivery_address_name": address2.name,
				"description_of_content": "Test Shipment",
				"value_of_goods": 10,
				"pickup_date": frappe.utils.now(),
				"shipment_parcel": [{"length": 10, "width": 12, "height": 20, "weight": 0, "count": 1}],
			}
		)
		msg = "Parcel weight cannot be 0"
		with self.assertRaises(frappe.ValidationError, msg=msg):
			shipment.insert()

	# codecov
	def test_on_submit_TC_SCK_354(self):
		address1 = create_address(**self.args1)
		address2 = create_address(**self.args2)

		shipment = frappe.get_doc(
			{
				"doctype": "Shipment",
				"pickup_from_type": "Company",
				"pickup_address_name": address1.name,
				"pickup_contact_person": "Administrator",
				"delivery_address_name": address2.name,
				"description_of_content": "Test Shipment",
				"value_of_goods": 0,
				"pickup_date": frappe.utils.now(),
				"shipment_parcel": [{"length": 10, "width": 12, "height": 20, "weight": 12, "count": 1}],
			}
		)
		shipment.insert()
		shipment.reload()
		msg = "Value of goods cannot be 0"
		with self.assertRaises(frappe.ValidationError, msg=msg):
			shipment.submit()

	# codecov
	def test_on_submit_no_shipment_parcel_TC_SCK_355(self):
		address1 = create_address(**self.args1)
		address2 = create_address(**self.args2)

		shipment = frappe.get_doc(
			{
				"doctype": "Shipment",
				"pickup_from_type": "Company",
				"pickup_address_name": address1.name,
				"pickup_contact_person": "Administrator",
				"delivery_address_name": address2.name,
				"description_of_content": "Test Shipment",
				"value_of_goods": 0,
				"pickup_date": frappe.utils.now(),
			}
		)
		shipment.insert()
		shipment.reload()
		msg = "Please enter Shipment Parcel information"
		with self.assertRaises(frappe.ValidationError, msg=msg):
			shipment.submit()
		shipment.reload()
		shipment.cancel()

	# codecov
	def test_validate_pickup_time_TC_SCK_356(self):
		address1 = create_address(**self.args1)
		address2 = create_address(**self.args2)

		shipment = frappe.get_doc(
			{
				"doctype": "Shipment",
				"pickup_from_type": "Company",
				"pickup_address_name": address1.name,
				"pickup_contact_person": "Administrator",
				"delivery_address_name": address2.name,
				"description_of_content": "Test Shipment",
				"value_of_goods": 0,
				"pickup_date": add_to_date(now(), hours=-1),
				"pickup_from": add_to_date(now(), hours=+1),
				"pickup_to": frappe.utils.now(),
				"shipment_parcel": [{"length": 10, "width": 12, "height": 20, "weight": 12, "count": 1}],
			}
		)
		msg = "Pickup To time should be greater than Pickup From time"
		with self.assertRaises(frappe.ValidationError, msg=msg):
			shipment.insert()

	# codecov
	def test_whitelisted_methods_TC_SCK_357(self):
		from erpnext.stock.doctype.shipment.shipment import (
			get_address_name,
			get_company_contact,
			get_contact_name,
		)

		address1 = create_address(**self.args1)

		address2 = create_address(**self.args2)

		shipment = frappe.get_doc(
			{
				"doctype": "Shipment",
				"pickup_from_type": "Company",
				"pickup_address_name": address1.name,
				"pickup_contact_person": "Administrator",
				"delivery_address_name": address2.name,
				"description_of_content": "Test Shipment",
				"value_of_goods": 0,
				"pickup_date": add_to_date(now(), hours=+1),
				"pickup_from": add_to_date(now(), hours=-1),
				"pickup_to": frappe.utils.now(),
				"shipment_parcel": [{"length": 10, "width": 12, "height": 20, "weight": 12, "count": 1}],
			}
		)
		shipment.insert()
		get_address_name("Shipment", shipment.name)
		get_contact_name("Shipment", shipment.name)
		self.assertEqual(shipment.pickup_address_name, address1.name)

	# codecov
	def test_get_company_contact_TC_SCK_392(self):
		from erpnext.stock.doctype.shipment.shipment import get_company_contact

		# Create test user directly
		user_email = "testuser@example.com"
		if frappe.db.exists("User", user_email):
			frappe.delete_doc("User", user_email, force=1)

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": user_email,
				"first_name": "Test",
				"last_name": "User",
				"mobile_no": "9876543210",
				"gender": "Male",
			}
		).insert(ignore_permissions=True)

		# Call the function
		result = get_company_contact(user)

		# Assertions
		self.assertEqual(result["first_name"], "Test")
		self.assertEqual(result["last_name"], "User")
		self.assertEqual(result["email"], "testuser@example.com")
		self.assertEqual(result["mobile_no"], "9876543210")
		self.assertEqual(result["phone"], "9876543210")  # fallback works
		self.assertEqual(result["gender"], "Male")

	def test_get_total_weight(self):
		shipment = frappe.new_doc("Shipment")
		shipment.extend(
			"shipment_parcel",
			[
				{"length": 5, "width": 5, "height": 5, "weight": 5, "count": 5},
				{"length": 5, "width": 5, "height": 5, "weight": 10, "count": 1},
			],
		)
		self.assertEqual(shipment.get_total_weight(), 35)


def create_test_delivery_note():
	company = get_shipment_company()
	customer = get_shipment_customer()
	item = get_shipment_item(company.name)
	posting_date = date.today() + timedelta(days=1)

	create_material_receipt(item, company.name)
	delivery_note = frappe.new_doc("Delivery Note")
	delivery_note.company = company.name
	delivery_note.posting_date = posting_date.strftime("%Y-%m-%d")
	delivery_note.posting_time = "10:00"
	delivery_note.customer = customer.name
	delivery_note.append(
		"items",
		{
			"item_code": item.name,
			"item_name": item.item_name,
			"description": "Test delivery note for shipment",
			"qty": 5,
			"uom": "Nos",
			"warehouse": "Stores - _TC",
			"rate": item.standard_rate,
			"cost_center": "Main - _TC",
		},
	)
	delivery_note.insert()
	return delivery_note


def create_test_shipment(delivery_notes=None):
	company = get_shipment_company()
	company_address = get_shipment_company_address(company.name)
	customer = get_shipment_customer()
	customer_address = get_shipment_customer_address(customer.name)
	customer_contact = get_shipment_customer_contact(customer.name)
	posting_date = date.today() + timedelta(days=5)

	shipment = frappe.new_doc("Shipment")
	shipment.pickup_from_type = "Company"
	shipment.pickup_company = company.name
	shipment.pickup_address_name = company_address.name
	shipment.delivery_to_type = "Customer"
	shipment.delivery_customer = customer.name
	shipment.delivery_address_name = customer_address.name
	shipment.delivery_contact_name = customer_contact.name
	shipment.pallets = "No"
	shipment.shipment_type = "Goods"
	shipment.value_of_goods = 1000
	shipment.pickup_type = "Pickup"
	shipment.pickup_date = posting_date.strftime("%Y-%m-%d")
	shipment.pickup_from = "09:00"
	shipment.pickup_to = "17:00"
	shipment.description_of_content = "unit test entry"
	for delivery_note in delivery_notes:
		shipment.append("shipment_delivery_note", {"delivery_note": delivery_note.name})
	shipment.append("shipment_parcel", {"length": 5, "width": 5, "height": 5, "weight": 5, "count": 5})
	shipment.insert()
	return shipment


def get_shipment_customer_contact(customer_name):
	contact_fname = "Customer Shipment"
	contact_lname = "Testing"
	customer_name = contact_fname + " " + contact_lname
	contacts = frappe.get_all("Contact", fields=["name"], filters={"name": customer_name})
	if len(contacts):
		return contacts[0]
	else:
		return create_customer_contact(contact_fname, contact_lname)


def get_shipment_customer_address(customer_name):
	address_title = customer_name + " address 123"
	customer_address = frappe.get_all("Address", fields=["name"], filters={"address_title": address_title})
	if len(customer_address):
		return customer_address[0]
	else:
		return create_shipment_address(address_title, customer_name, 81929)


def get_shipment_customer():
	customer_name = "Shipment Customer"
	customer = frappe.get_all("Customer", fields=["name"], filters={"name": customer_name})
	if len(customer):
		return customer[0]
	else:
		return create_shipment_customer(customer_name)


def get_shipment_company_address(company_name):
	address_title = company_name + " address 123"
	addresses = frappe.get_all("Address", fields=["name"], filters={"address_title": address_title})
	if len(addresses):
		return addresses[0]
	else:
		return create_shipment_address(address_title, company_name, 80331)


def get_shipment_company():
	return frappe.get_doc("Company", "_Test Company")


def get_shipment_item(company_name):
	item_name = "Testing Shipment item"
	items = frappe.get_all(
		"Item",
		fields=["name", "item_name", "item_code", "standard_rate"],
		filters={"item_name": item_name},
	)
	if len(items):
		return items[0]
	else:
		return create_shipment_item(item_name, company_name)


def create_shipment_address(address_title, company_name, postal_code):
	address = frappe.new_doc("Address")
	address.address_title = address_title
	address.address_type = "Shipping"
	address.address_line1 = company_name + " address line 1"
	address.city = "Random City"
	address.postal_code = postal_code
	address.country = "Germany"
	address.insert()
	return address


def create_customer_contact(fname, lname):
	customer = frappe.new_doc("Contact")
	customer.customer_name = fname + " " + lname
	customer.first_name = fname
	customer.last_name = lname
	customer.is_primary_contact = 1
	customer.is_billing_contact = 1
	customer.append("email_ids", {"email_id": "randomme@email.com", "is_primary": 1})
	customer.append("phone_nos", {"phone": "123123123", "is_primary_phone": 1, "is_primary_mobile_no": 1})
	customer.status = "Passive"
	customer.insert()
	return customer


def create_shipment_customer(customer_name):
	customer = frappe.new_doc("Customer")
	customer.customer_name = customer_name
	customer.customer_type = "Company"
	customer.customer_group = "All Customer Groups"
	customer.territory = "All Territories"
	customer.insert()
	return customer


def create_material_receipt(item, company):
	posting_date = date.today()
	stock = frappe.new_doc("Stock Entry")
	stock.company = company
	stock.stock_entry_type = "Material Receipt"
	stock.posting_date = posting_date.strftime("%Y-%m-%d")
	stock.append(
		"items",
		{
			"t_warehouse": "Stores - _TC",
			"item_code": item.name,
			"qty": 5,
			"uom": "Nos",
			"basic_rate": item.standard_rate,
			"cost_center": "Main - _TC",
		},
	)
	stock.insert()
	stock.submit()


def create_shipment_item(item_name, company_name):
	item = frappe.new_doc("Item")
	item.item_name = item_name
	item.item_code = item_name
	item.item_group = "All Item Groups"
	item.stock_uom = "Nos"
	item.standard_rate = 50
	item.append("item_defaults", {"company": company_name, "default_warehouse": "Stores - _TC"})
	if "india_compliance" in frappe.get_installed_apps():
		item.gst_hsn_code = get_hsn()
	item.insert()
	return item
