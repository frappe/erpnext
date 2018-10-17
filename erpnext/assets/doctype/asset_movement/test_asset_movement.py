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
		make_serialized_item()

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

		movement1 = create_asset_movement(asset= asset.name, purpose = 'Transfer',
			company=asset.company, source_location="Test Location", target_location="Test Location 2")
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "Test Location 2")

		movement2 = create_asset_movement(asset= asset.name, purpose = 'Transfer',
			company=asset.company, source_location = "Test Location 2", target_location="Test Location")
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "Test Location")

		movement1.cancel()
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "Test Location")

		movement2.cancel()
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "Test Location")

	def test_movement_for_serialized_asset(self):
		asset_item = "Test Serialized Asset Item"
		pr = make_purchase_receipt(item_code=asset_item, rate = 1000, qty=3, location = "Mumbai")
		asset_name = frappe.db.get_value('Asset', {'purchase_receipt': pr.name}, 'name')

		asset = frappe.get_doc('Asset', asset_name)
		month_end_date = get_last_day(nowdate())
		asset.available_for_use_date = nowdate() if nowdate() != month_end_date else add_days(nowdate(), -15)

		asset.calculate_depreciation = 1
		asset.append("finance_books", {
			"expected_value_after_useful_life": 200,
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": month_end_date
		})
		asset.submit()
		serial_nos = frappe.db.get_value('Asset Movement', {'reference_name': pr.name}, 'serial_no')

		mov1 = create_asset_movement(asset=asset_name, purpose = 'Transfer',
			company=asset.company, source_location = "Mumbai", target_location="Pune", serial_no=serial_nos)
		self.assertEqual(mov1.target_location, "Pune")

		serial_no = frappe.db.get_value('Serial No', {'asset': asset_name}, 'name')

		employee = make_employee("testassetemp@example.com")
		create_asset_movement(asset=asset_name, purpose = 'Transfer',
			company=asset.company, serial_no=serial_no, to_employee=employee)

		self.assertEqual(frappe.db.get_value('Serial No', serial_no, 'employee'), employee)

		create_asset_movement(asset=asset_name, purpose = 'Transfer', company=asset.company,
			serial_no=serial_no, from_employee=employee, to_employee="_T-Employee-00001")

		self.assertEqual(frappe.db.get_value('Serial No', serial_no, 'location'), "Pune")

		mov4 = create_asset_movement(asset=asset_name, purpose = 'Transfer',
			company=asset.company, source_location = "Pune", target_location="Nagpur", serial_no=serial_nos)
		self.assertEqual(mov4.target_location, "Nagpur")
		self.assertEqual(frappe.db.get_value('Serial No', serial_no, 'location'), "Nagpur")
		self.assertEqual(frappe.db.get_value('Serial No', serial_no, 'employee'), "_T-Employee-00001")

def create_asset_movement(**args):
	args = frappe._dict(args)

	if not args.transaction_date:
		args.transaction_date = now()

	movement = frappe.new_doc("Asset Movement")
	movement.update({
		"asset": args.asset,
		"transaction_date": args.transaction_date,
		"target_location": args.target_location,
		"company": args.company,
		'purpose': args.purpose or 'Receipt',
		'serial_no': args.serial_no,
		'quantity': len(get_serial_nos(args.serial_no)) if args.serial_no else 1,
		'from_employee': "_T-Employee-00001" or args.from_employee,
		'to_employee': args.to_employee
	})

	if args.source_location:
		movement.update({
			'source_location': args.source_location
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

def make_serialized_item():
	asset_item = "Test Serialized Asset Item"

	if not frappe.db.exists('Item', asset_item):
		asset_category = frappe.get_all('Asset Category')

		if asset_category:
			asset_category = asset_category[0].name

		if not asset_category:
			doc = frappe.get_doc({
				'doctype': 'Asset Category',
				'asset_category_name': 'Test Asset Category',
				'depreciation_method': 'Straight Line',
				'total_number_of_depreciations': 12,
				'frequency_of_depreciation': 1,
				'accounts': [{
					'company_name': '_Test Company',
					'fixed_asset_account': '_Test Fixed Asset - _TC',
					'accumulated_depreciation_account': 'Depreciation - _TC',
					'depreciation_expense_account': 'Depreciation - _TC'
				}]
			}).insert()

			asset_category = doc.name

		make_item(asset_item, {'is_stock_item':0,
			'stock_uom': 'Box', 'is_fixed_asset': 1, 'has_serial_no': 1,
			'asset_category': asset_category, 'serial_no_series': 'ABC.###'})
