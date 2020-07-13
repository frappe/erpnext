# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
import json
from datetime import date, timedelta

import frappe
import unittest
from erpnext.stock.doctype.shipment.shipment import fetch_shipping_rates
from erpnext.stock.doctype.shipment.shipment import create_shipment
from erpnext.stock.doctype.shipment.shipment import update_tracking

class TestShipment(unittest.TestCase):
	pass

	def test_shipment_booking(self):
		shipment = create_test_shipment()
		try:
			shipment.submit()
		except:
			frappe.throw('Error occurred on submit shipment')
		doc, rate, tracking_data = make_shipment_transaction(shipment)
		if doc and rate and tracking_data:
			self.assertEqual(doc.service_provider, rate.get('service_provider'))
			self.assertEqual(doc.shipment_amount, rate.get('actual_price'))
			self.assertEqual(doc.carrier, rate.get('carrier'))
			self.assertEqual(doc.tracking_status, tracking_data.get('tracking_status'))
			self.assertEqual(doc.tracking_url, tracking_data.get('tracking_url'))

	def test_shipment_from_delivery_note(self):
		delivery_note = create_test_delivery_note()
		try:
			delivery_note.submit()
		except:
			frappe.throw('An error occurred.')
		
		shipment = create_test_shipment([ delivery_note ])
		try:
			shipment.submit()
		except:
			frappe.throw('Error occurred on submit shipment')
		doc, rate, tracking_data = make_shipment_transaction(shipment)
		if doc and rate and tracking_data:
			self.assertEqual(doc.service_provider, rate.get('service_provider'))
			self.assertEqual(doc.shipment_amount, rate.get('actual_price'))
			self.assertEqual(doc.carrier, rate.get('carrier'))
			self.assertEqual(doc.tracking_status, tracking_data.get('tracking_status'))
			self.assertEqual(doc.tracking_url, tracking_data.get('tracking_url'))

		

def make_shipment_transaction(shipment):
	shipment_parcel = convert_shipmet_parcel(shipment.shipment_parcel)
	shipment_rates = fetch_shipping_rates(shipment.pickup_from_type, shipment.delivery_to_type, 
		shipment.pickup_address_name, shipment.delivery_address_name,
		shipment_parcel, shipment.description_of_content,
		shipment.pickup_date, shipment.value_of_goods,
		pickup_contact_name=shipment.pickup_contact_name,
		delivery_contact_name=shipment.delivery_contact_name
	)
	if len(shipment_rates) > 0:
		# We are taking the first shipment rate
		rate = shipment_rates[0]
		new_shipment = create_shipment(
			shipment=shipment.name,
			pickup_from_type=shipment.pickup_from_type,
			delivery_to_type=shipment.delivery_to_type,
			pickup_address_name=shipment.pickup_address_name,
			delivery_address_name=shipment.delivery_address_name,
			shipment_parcel=shipment_parcel,
			description_of_content=shipment.description_of_content,
			pickup_date=shipment.pickup_date,
			pickup_contact_name=shipment.pickup_contact_name,
			delivery_contact_name=shipment.delivery_contact_name,
			value_of_goods=shipment.value_of_goods,
			service_data=json.dumps(rate),
			shipment_notific_email=None,
			tracking_notific_email=None,
			delivery_notes=None
		)
		service_provider = rate.get('service_provider')
		shipment_id = new_shipment.get('shipment_id')
		tracking_data = update_tracking(
			shipment.name,
			service_provider,
			shipment_id,
			delivery_notes=None
		)
		doc = frappe.get_doc('Shipment', shipment.name)
		return doc, rate, tracking_data
	return None, None, None

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
	frappe.db.commit()
	return delivery_note


def create_test_shipment(delivery_notes=[]):
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
		shipment.append('shipment_delivery_notes', 
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
	frappe.db.commit()
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
	try:
		stock.submit()
	except:
		frappe.throw('An error occurred.')
	

def create_shipment_item(item_name, company_name):
	item = frappe.new_doc("Item")
	item.item_name = item_name
	item.item_code = item_name
	item.item_group = 'All Item Groups'
	item.opening_stock = 'Nos'
	item.standard_rate = 50
	item.append('item_defaults',
		{
			"company": company_name,
			"default_warehouse": 'Stores - SC'
		}
	)
	try:
		item.insert()
	except:
		frappe.throw('An error occurred.')
	return item


def convert_shipmet_parcel(shipmet_parcel):
	data = []
	for parcel in shipmet_parcel:
		data.append(
			{
				"length": parcel.length,
				"width": parcel.width,
				"height": parcel.height,
				"weight": parcel.weight,
				"count": parcel.count
			}
		)
	return json.dumps(data)
