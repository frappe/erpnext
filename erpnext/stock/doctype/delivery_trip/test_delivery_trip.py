# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import erpnext
import frappe
from erpnext.stock.doctype.delivery_trip.delivery_trip import get_contact_and_address, notify_customers
from erpnext.tests.utils import create_test_contact_and_address
from frappe.utils import add_days, flt, now_datetime, nowdate


class TestDeliveryTrip(unittest.TestCase):
	def setUp(self):
		driver = create_driver()
		create_vehicle()
		create_delivery_notification()
		create_test_contact_and_address()
		address = create_address(driver)

		self.delivery_trip = create_delivery_trip(driver, address)

	def tearDown(self):
		frappe.db.sql("delete from `tabDriver`")
		frappe.db.sql("delete from `tabVehicle`")
		frappe.db.sql("delete from `tabEmail Template`")
		frappe.db.sql("delete from `tabDelivery Trip`")

	def test_delivery_trip_notify_customers(self):
		notify_customers(delivery_trip=self.delivery_trip.name)
		self.delivery_trip.load_from_db()
		self.assertEqual(self.delivery_trip.email_notification_sent, 1)

	def test_unoptimized_route_list_without_locks(self):
		route_list = self.delivery_trip.form_route_list(optimize=False)

		# Return a single list of destinations, from home address and back
		self.assertEqual(len(route_list), 1)
		self.assertEqual(len(route_list[0]), 4)

	def test_unoptimized_route_list_with_locks(self):
		self.delivery_trip.delivery_stops[0].lock = 1
		self.delivery_trip.save()
		route_list = self.delivery_trip.form_route_list(optimize=False)

		# Return a single list of destinations, from home address and back,
		# since the stops don't need to optimized and simple time
		# estimation is enough
		self.assertEqual(len(route_list), 1)
		self.assertEqual(len(route_list[0]), 4)

	def test_optimized_route_list_without_locks(self):
		route_list = self.delivery_trip.form_route_list(optimize=True)

		# Return a single list of destinations, from home address and back,
		# since the route doesn't have any locks to be optimized against
		self.assertEqual(len(route_list), 1)
		self.assertEqual(len(route_list[0]), 4)

	def test_optimized_route_list_with_locks(self):
		self.delivery_trip.delivery_stops[0].lock = 1
		self.delivery_trip.save()
		route_list = self.delivery_trip.form_route_list(optimize=True)

		# Return multiple route lists, taking the home address as start and end
		self.assertEqual(len(route_list), 2)
		self.assertEqual(len(route_list[0]), 2)  # [home_address, locked_stop]
		self.assertEqual(len(route_list[1]), 3)  # [locked_stop, second_stop, home_address]

	def test_delivery_trip_status_draft(self):
		self.assertEqual(self.delivery_trip.status, "Draft")

	def test_delivery_trip_status_scheduled(self):
		self.delivery_trip.submit()
		self.assertEqual(self.delivery_trip.status, "Scheduled")

	def test_delivery_trip_status_cancelled(self):
		self.delivery_trip.submit()
		self.delivery_trip.cancel()
		self.assertEqual(self.delivery_trip.status, "Cancelled")

	def test_delivery_trip_status_in_transit(self):
		self.delivery_trip.submit()
		self.delivery_trip.delivery_stops[0].visited = 1
		self.delivery_trip.save()
		self.assertEqual(self.delivery_trip.status, "In Transit")

	def test_delivery_trip_status_completed(self):
		self.delivery_trip.submit()

		for stop in self.delivery_trip.delivery_stops:
			stop.visited = 1

		self.delivery_trip.save()
		self.assertEqual(self.delivery_trip.status, "Completed")

def create_address(driver):
	if not frappe.db.exists("Address", {"address_title": "_Test Address for Driver"}):
		address = frappe.get_doc({
			"doctype": "Address",
			"address_title": "_Test Address for Driver",
			"address_type": "Office",
			"address_line1": "Station Road",
			"city": "_Test City",
			"state": "Test State",
			"country": "India",
			"links":[
				{
					"link_doctype": "Driver",
					"link_name": driver.name
				}
			]
		}).insert(ignore_permissions=True)

		frappe.db.set_value("Driver", driver.name, "address", address.name)

		return address

	return frappe.get_doc("Address", {"address_title": "_Test Address for Driver"})

def create_driver():
	if not frappe.db.exists("Driver", {"full_name": "Newton Scmander"}):
		driver = frappe.get_doc({
			"doctype": "Driver",
			"full_name": "Newton Scmander",
			"cell_number": "98343424242",
			"license_number": "B809",
		}).insert(ignore_permissions=True)

		return driver

	return frappe.get_doc("Driver", {"full_name": "Newton Scmander"})

def create_delivery_notification():
	if not frappe.db.exists("Email Template", "Delivery Notification"):
		dispatch_template = frappe.get_doc({
			'doctype': 'Email Template',
			'name': 'Delivery Notification',
			'response': 'Test Delivery Trip',
			'subject': 'Test Subject',
			'owner': frappe.session.user
		})
		dispatch_template.insert()

	delivery_settings = frappe.get_single("Delivery Settings")
	delivery_settings.dispatch_template = 'Delivery Notification'
	delivery_settings.save()


def create_vehicle():
	if not frappe.db.exists("Vehicle", "JB 007"):
		vehicle = frappe.get_doc({
			"doctype": "Vehicle",
			"license_plate": "JB 007",
			"make": "Maruti",
			"model": "PCM",
			"last_odometer": 5000,
			"acquisition_date": nowdate(),
			"location": "Mumbai",
			"chassis_no": "1234ABCD",
			"uom": "Litre",
			"vehicle_value": flt(500000)
		})
		vehicle.insert()


def create_delivery_trip(driver, address, contact=None):
	if not contact:
		contact = get_contact_and_address("_Test Customer")

	delivery_trip = frappe.get_doc({
		"doctype": "Delivery Trip",
		"company": erpnext.get_default_company(),
		"departure_time": add_days(now_datetime(), 5),
		"driver": driver.name,
		"driver_address": address.name,
		"vehicle": "JB 007",
		"delivery_stops": [{
			"customer": "_Test Customer",
			"address": contact.shipping_address.parent,
			"contact": contact.contact_person.parent
		},
		{
			"customer": "_Test Customer",
			"address": contact.shipping_address.parent,
			"contact": contact.contact_person.parent
		}]
	}).insert(ignore_permissions=True)

	return delivery_trip
