# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestGoogleMaps(unittest.TestCase):

	def test_google_maps(self):
		driver = create_driver()
		address = create_address()
		integration = enable_integration(driver, address)

		gmaps = frappe.get_doc("Google Maps", {"driver": driver.name})

		self.assertEqual(integration.driver, gmaps.driver)
		self.assertEqual(integration.address, gmaps.address)

def create_address():
	if not frappe.db.exists('Address', {"address_title": "_Test Address for Customer"}):
		frappe.get_doc(dict(
			doctype='Address',
			address_title='_Test Address for Customer',
			address_type='Office',
			address_line1='Station Road',
			city='_Test City',
			state='Test State',
			country='India',
			links = [dict(
				link_doctype='Customer',
				link_name='_Test Customer'
			)]
		)).insert(ignore_permissions=True)

	return frappe.get_doc('Address', {"address_title": "_Test Address for Customer"})

def create_driver():
	if not frappe.db.exists("Driver", {"full_name": "Newton Scmander"}):
		frappe.get_doc({
			"doctype": "Driver",
			"full_name": "Newton Scmander",
			"cell_number": "98343424242",
			"license_number": "B809"
		}).insert(ignore_permissions=True)

	return frappe.get_doc("Driver", {"full_name": "Newton Scmander"})

def enable_integration(driver, address):
	if not frappe.db.exists("Google Maps", {"driver": driver.name}):
		frappe.get_doc({
			"doctype": "Google Maps",
			"enable": 1,
			"driver": driver.name,
			"address": address.name
		}).insert(ignore_permissions=True)

	return frappe.get_doc("Google Maps", {"driver": driver.name})