# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

from datetime import date, timedelta

import frappe

from erpnext.stock.doctype.delivery_note.delivery_note import make_shipment
from erpnext.tests.utils import ERPNextTestCase


class TestShipment(ERPNextTestCase):
	def test_shipment_from_delivery_note(self):
		delivery_note = create_test_delivery_note()
		delivery_note.submit()
		shipment = create_test_shipment([ delivery_note ])
		shipment.submit()
		second_shipment = make_shipment(delivery_note.name)
		self.assertEqual(second_shipment.value_of_goods, delivery_note.grand_total)
		self.assertEqual(len(second_shipment.shipment_delivery_note), 1)
		self.assertEqual(second_shipment.shipment_delivery_note[0].delivery_note, delivery_note.name)

def create_test_delivery_note():
	company = get_shipment_company()
	customer = get_shipment_customer()
	item = get_shipment_item(company.name)
	posting_date = date.today() + timedelta(days=1)

	create_material_receipt(item, company.name)
	delivery_note = frappe.new_doc("Delivery Note")
	delivery_note.company = company.name
	delivery_note.posting_date = posting_date.strftime("%Y-%m-%d")
	delivery_note.posting_time = '10:00'
	delivery_note.customer = customer.name
	delivery_note.append('items',
		{
			"item_code": item.name,
			"item_name": item.item_name,
			"description": 'Test delivery note for shipment',
			"qty": 5,
			"uom": 'Nos',
			"warehouse": 'Stores - SC',
			"rate": item.standard_rate,
			"cost_center": 'Main - SC'
		}
	)
	delivery_note.insert()
	return delivery_note


def create_test_shipment(delivery_notes = None):
	company = get_shipment_company()
	company_address = get_shipment_company_address(company.name)
	customer = get_shipment_customer()
	customer_address = get_shipment_customer_address(customer.name)
	customer_contact = get_shipment_customer_contact(customer.name)
	posting_date = date.today() + timedelta(days=5)

	shipment = frappe.new_doc("Shipment")
	shipment.pickup_from_type = 'Company'
	shipment.pickup_company = company.name
	shipment.pickup_address_name = company_address.name
	shipment.delivery_to_type = 'Customer'
	shipment.delivery_customer = customer.name
	shipment.delivery_address_name = customer_address.name
	shipment.delivery_contact_name = customer_contact.name
	shipment.pallets = 'No'
	shipment.shipment_type = 'Goods'
	shipment.value_of_goods = 1000
	shipment.pickup_type = 'Pickup'
	shipment.pickup_date = posting_date.strftime("%Y-%m-%d")
	shipment.pickup_from = '09:00'
	shipment.pickup_to = '17:00'
	shipment.description_of_content = 'unit test entry'
	for delivery_note in delivery_notes:
		shipment.append('shipment_delivery_note',
			{
				"delivery_note": delivery_note.name
			}
		)
	shipment.append('shipment_parcel',
		{
			"length": 5,
			"width": 5,
			"height": 5,
			"weight": 5,
			"count": 5
		}
	)
	shipment.insert()
	return shipment


def get_shipment_customer_contact(customer_name):
	contact_fname = 'Customer Shipment'
	contact_lname = 'Testing'
	customer_name = contact_fname + ' ' + contact_lname
	contacts = frappe.get_all("Contact", fields=["name"], filters = {"name": customer_name})
	if len(contacts):
		return contacts[0]
	else:
		return create_customer_contact(contact_fname, contact_lname)


def get_shipment_customer_address(customer_name):
	address_title = customer_name + ' address 123'
	customer_address = frappe.get_all("Address", fields=["name"], filters = {"address_title": address_title})
	if len(customer_address):
		return customer_address[0]
	else:
		return create_shipment_address(address_title, customer_name, 81929)

def get_shipment_customer():
	customer_name = 'Shipment Customer'
	customer = frappe.get_all("Customer", fields=["name"], filters = {"name": customer_name})
	if len(customer):
		return customer[0]
	else:
		return create_shipment_customer(customer_name)

def get_shipment_company_address(company_name):
	address_title = company_name + ' address 123'
	addresses = frappe.get_all("Address", fields=["name"], filters = {"address_title": address_title})
	if len(addresses):
		return addresses[0]
	else:
		return create_shipment_address(address_title, company_name, 80331)

def get_shipment_company():
	company_name = 'Shipment Company'
	abbr = 'SC'
	companies = frappe.get_all("Company", fields=["name"], filters = {"company_name": company_name})
	if len(companies):
		return companies[0]
	else:
		return create_shipment_company(company_name, abbr)

def get_shipment_item(company_name):
	item_name = 'Testing Shipment item'
	items = frappe.get_all("Item",
		fields=["name", "item_name", "item_code", "standard_rate"],
		filters = {"item_name": item_name}
	)
	if len(items):
		return items[0]
	else:
		return create_shipment_item(item_name, company_name)

def create_shipment_address(address_title, company_name, postal_code):
	address = frappe.new_doc("Address")
	address.address_title = address_title
	address.address_type = 'Shipping'
	address.address_line1 = company_name + ' address line 1'
	address.city = 'Random City'
	address.postal_code = postal_code
	address.country = 'Germany'
	address.insert()
	return address


def create_customer_contact(fname, lname):
	customer = frappe.new_doc("Contact")
	customer.customer_name = fname + ' ' + lname
	customer.first_name = fname
	customer.last_name = lname
	customer.is_primary_contact = 1
	customer.is_billing_contact = 1
	customer.append('email_ids',
		{
			'email_id': 'randomme@email.com',
			'is_primary': 1
		}
	)
	customer.append('phone_nos',
		{
			'phone': '123123123',
			'is_primary_phone': 1,
			'is_primary_mobile_no': 1
		}
	)
	customer.status = 'Passive'
	customer.insert()
	return customer


def create_shipment_company(company_name, abbr):
	company = frappe.new_doc("Company")
	company.company_name = company_name
	company.abbr = abbr
	company.default_currency = 'EUR'
	company.country = 'Germany'
	company.enable_perpetual_inventory = 0
	company.insert()
	return company

def create_shipment_customer(customer_name):
	customer = frappe.new_doc("Customer")
	customer.customer_name = customer_name
	customer.customer_type = 'Company'
	customer.customer_group = 'All Customer Groups'
	customer.territory = 'All Territories'
	customer.gst_category = 'Unregistered'
	customer.insert()
	return customer

def create_material_receipt(item, company):
	posting_date = date.today()
	stock = frappe.new_doc("Stock Entry")
	stock.company = company
	stock.stock_entry_type = 'Material Receipt'
	stock.posting_date = posting_date.strftime("%Y-%m-%d")
	stock.append('items',
		{
			"t_warehouse": 'Stores - SC',
			"item_code": item.name,
			"qty": 5,
			"uom": 'Nos',
			"basic_rate": item.standard_rate,
			"cost_center": 'Main - SC'
		}
	)
	stock.insert()
	stock.submit()


def create_shipment_item(item_name, company_name):
	item = frappe.new_doc("Item")
	item.item_name = item_name
	item.item_code = item_name
	item.item_group = 'All Item Groups'
	item.stock_uom = 'Nos'
	item.standard_rate = 50
	item.append('item_defaults',
		{
			"company": company_name,
			"default_warehouse": 'Stores - SC'
		}
	)
	item.insert()
	return item
