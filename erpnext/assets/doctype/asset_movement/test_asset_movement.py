# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.utils import now
import unittest
from erpnext.assets.doctype.asset.test_asset import create_asset


class TestAssetMovement(unittest.TestCase):
	def test_movement(self):
		asset = create_asset()

		if asset.docstatus == 0:
			asset.submit()
		if not frappe.db.exists("Location", "Test Location 2"):
			frappe.get_doc({
				'doctype': 'Location',
				'location_name': 'Test Location 2'
			}).insert()

		movement1 = create_asset_movement(asset, target_location="Test Location 2")
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "Test Location 2")

		movement2 = create_asset_movement(asset, target_location="Test Location")
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "Test Location")

		movement1.cancel()
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "Test Location")

		movement2.cancel()
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), "Test Location")

		asset.load_from_db()
		asset.cancel()
		frappe.delete_doc("Asset", asset.name)

def create_asset_movement(asset, target_location, transaction_date=None):
	if not transaction_date:
		transaction_date = now()

	movement = frappe.new_doc("Asset Movement")
	movement.update({
		"asset": asset.name,
		"transaction_date": transaction_date,
		"target_location": target_location,
		"company": asset.company
	})

	movement.insert()
	movement.submit()

	return movement
