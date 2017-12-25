# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import erpnext
import unittest
from frappe.utils import nowdate, add_days
from erpnext.tests.utils import create_test_contact_and_address
from erpnext.stock.doctype.delivery_trip.delivery_trip import notify_customers, get_contact_and_address

class TestDeliveryTrip(unittest.TestCase):
	def setUp(self):
		create_driver()
		create_vehicle()
		create_delivery_notfication()
		create_test_contact_and_address()

	def test_delivery_trip(self):
		contact = get_contact_and_address("_Test Customer")

		if not frappe.db.exists("Delivery Trip", "TOUR-00000"):
			delivery_trip = frappe.new_doc("Delivery Trip")
			delivery_trip.company = erpnext.get_default_company()
			delivery_trip.date = add_days(nowdate(), 5)
			delivery_trip.driver = "DRIVER-00001"
			delivery_trip.vehicle = "JB 007"
			delivery_trip.append("delivery_stops", {
				"customer": "_Test Customer",
				"address": contact.shipping_address.parent,
				"contact": contact.contact_person.parent
			})
			delivery_trip.delivery_notification = 'Delivery Notification'
			delivery_trip.insert()
			sender_email = frappe.db.get_value("User", frappe.session.user, "email")
			notify_customers(docname=delivery_trip.name, date=delivery_trip.date, driver=delivery_trip.driver,
							 vehicle=delivery_trip.vehicle,
							 sender_email=sender_email, delivery_notification=delivery_trip.delivery_notification)

			self.assertEquals(delivery_trip.get("delivery_stops")[0].notified_by_email, 0)

def create_driver():
	if not frappe.db.exists("Driver", "Newton Scmander"):
		driver = frappe.new_doc("Driver")
		driver.full_name = "Newton Scmander"
		driver.cell_number = "98343424242"
		driver.license_number = "B809"
		driver.insert()

def create_delivery_notfication():
	if not frappe.db.exists("Standard Reply", "Delivery Notification"):
		frappe.get_doc({
			'doctype': 'Standard Reply',
			'name': 'Delivery Notification',
			'response': 'Test Delivery Trip',
			'subject': 'Test Subject',
			'owner': frappe.session.user
		}).insert()

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
