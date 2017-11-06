# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import erpnext
import unittest
from frappe.utils import nowdate, add_days
from erpnext.tests.utils import create_test_contact_and_address
from erpnext.stock.doctype.delivery.delivery import notify_customers
from frappe.utils.user import get_user_fullname

class TestDelivery(unittest.TestCase):
	def setUp(self):
		create_driver()
		create_vehicle()
		create_test_contact_and_address()

	def test_delivery(self):
		delivery = frappe.new_doc("Delivery")
		delivery.company =  erpnext.get_default_company()
		delivery.date = add_days(nowdate(), 5)
		delivery.driver = "Newton Scmander"
		delivery.vehicle = "JB 007"
		delivery.append("delivery_stops", {
			"customer": "_Test Customer",
			"address": "_Test Address for Customer",
			"contact": '_Test Contact for _Test Customer -  _Test Customer'
		})
		delivery.insert()
		sender_email = frappe.db.get_value("User", frappe.session.user, "email")
		notify_customers(docname = delivery.name, date = delivery.date, driver = delivery.driver, vehicle = delivery.vehicle, 
			sender_email = sender_email, sender_name =  get_user_fullname(frappe.session['user']),
			delivery_notification = delivery.delivery_notification)

		self.assertEquals(delivery.get("delivery_stops")[0].notified_by_email, 1)

def create_driver():
	if not frappe.db.exists("Driver", "Newton Scmander"):
		driver = frappe.new_doc("Driver")
		driver.full_name = "Newton Scmander"
		driver.cell_number = "98343424242"
		driver.license_number = "B809"
		driver.append("driving_licence_category", {
			"class": "L"
		})
		driver.insert()

def create_vehicle():
	if not frappe.db.exists("Vehicle", "JB 007"):
		vehicle = frappe.get_doc({
			"doctype": "Vehicle",
			"license_plate": "JB 007",
			"make": "Maruti",
			"model": "PCM",
			"last_odometer":5000,
			"acquisition_date":frappe.utils.nowdate(),
			"location": "Mumbai",
			"chassis_no": "1234ABCD",
			"vehicle_value":frappe.utils.flt(500000)
		})
		vehicle.insert()