# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.stock.doctype.item.test_item import make_item
from frappe.utils import now, nowdate, get_last_day, add_days
from erpnext.assets.doctype.asset.test_asset import create_asset_data
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

class TestAssetMovement(unittest.TestCase):
	def setUp(self):
		create_asset_data()
		make_location()

	def test_movement(self):
		pr = make_purchase_receipt(item_code="Macbook Pro",
			qty=1, rate=100000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, 'name')
		asset = frappe.get_doc('Asset', asset_name)
		asset.calculate_depreciation = 1
		asset.available_for_use_date = '2020-06-06'
		asset.purchase_date = '2020-06-06'
		asset.append("finance_books", {
			"expected_value_after_useful_life": 10000,
			"next_depreciation_date": "2020-12-31",
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": "2020-06-06"
		})

		if asset.docstatus == 0:
			asset.submit()
		if not frappe.db.exists("Location", "Test Location 2"):
			frappe.get_doc({
				'doctype': 'Location',
				'location_name': 'Test Location 2'
			}).insert()

		movement1 = create_asset_movement(purpose = 'Transfer', company = asset.company, 
			assets = [{ 'asset': asset.name , 'source_location': 'Test Location', 'target_location': 'Test Location 2'}])
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "Test Location 2")

		movement2 = create_asset_movement(purpose = 'Transfer', company = asset.company, 
			assets = [{ 'asset': asset.name , 'source_location': 'Test Location 2', 'target_location': 'Test Location'}])
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "Test Location")

		employee = make_employee("testassetemp@example.com")
		movement3 = create_asset_movement(purpose = 'Transfer', company = asset.company, 
			assets = [{ 'asset': asset.name , 'source_location': 'Test Location', 'to_employee': employee}])
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "custodian"), employee)

		movement1.cancel()
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "Test Location")

		movement2.cancel()
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "Test Location")

def create_asset_movement(**args):
	args = frappe._dict(args)

	if not args.transaction_date:
		args.transaction_date = now()

	movement = frappe.new_doc("Asset Movement")
	movement.update({
		"assets": args.assets,
		"transaction_date": args.transaction_date,
		"company": args.company,
		'purpose': args.purpose or 'Receipt'
	})

	movement.insert()
	movement.submit()

	return movement

def make_location():
	for location in ['Pune', 'Mumbai', 'Nagpur']:
		if not frappe.db.exists('Location', location):
			frappe.get_doc({
				'doctype': 'Location',
				'location_name': location
			}).insert(ignore_permissions = True)
