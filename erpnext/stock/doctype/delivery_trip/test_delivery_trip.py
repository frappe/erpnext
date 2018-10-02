# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import erpnext
import frappe
from erpnext.stock.doctype.delivery_trip.delivery_trip import get_contact_and_address, notify_customers
from erpnext.tests.utils import create_test_contact_and_address
from frappe.utils import add_days, now_datetime, nowdate


class TestDeliveryTrip(unittest.TestCase):
	def setUp(self):
		create_driver()
		create_vehicle()
		create_delivery_notification()
		create_test_contact_and_address()

	def test_delivery_trip(self):
		contact = get_contact_and_address("_Test Customer")

		if not frappe.db.exists("Delivery Trip", "TOUR-00000"):
			delivery_trip = frappe.get_doc({
				"doctype": "Delivery Trip",
				"company": erpnext.get_default_company(),
				"date": add_days(nowdate(), 5),
				"departure_time": add_days(now_datetime(), 5),
				"driver": frappe.db.get_value('Driver', {"full_name": "Newton Scmander"}),
				"vehicle": "JB 007",
				"delivery_stops": [{
					"customer": "_Test Customer",
					"address": contact.shipping_address.parent,
					"contact": contact.contact_person.parent
				}]
			})
			delivery_trip.insert()

			notify_customers(delivery_trip=delivery_trip.name)
			delivery_trip.load_from_db()
			self.assertEqual(delivery_trip.email_notification_sent, 1)


def create_driver():
	if not frappe.db.exists("Driver", "Newton Scmander"):
		driver = frappe.get_doc({
			"doctype": "Driver",
			"full_name": "Newton Scmander",
			"cell_number": "98343424242",
			"license_number": "B809"
		})
		driver.insert()


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


def create_vehicle():
	if not frappe.db.exists("Vehicle", "JB 007"):
		vehicle = frappe.get_doc({
			"doctype": "Vehicle",
			"license_plate": "JB 007",
			"make": "Maruti",
			"model": "PCM",
			"last_odometer": 5000,
			"acquisition_date": frappe.utils.nowdate(),
			"location": "Mumbai",
			"chassis_no": "1234ABCD",
			"uom": "Litre",
			"vehicle_value": frappe.utils.flt(500000)
		})
		vehicle.insert()
