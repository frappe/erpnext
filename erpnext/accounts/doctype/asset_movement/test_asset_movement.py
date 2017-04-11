# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.utils import now
import unittest
from erpnext.accounts.doctype.asset.test_asset import create_asset


class TestAssetMovement(unittest.TestCase):
	def test_movement(self):
		asset = create_asset()
		
		if asset.docstatus == 0:
			asset.submit()
		
		movement1 = create_asset_movement(asset, target_warehouse="_Test Warehouse 1 - _TC")
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "warehouse"), "_Test Warehouse 1 - _TC")
		
		movement2 = create_asset_movement(asset, target_warehouse="_Test Warehouse 2 - _TC")
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "warehouse"), "_Test Warehouse 2 - _TC")
		
		movement1.cancel()
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "warehouse"), "_Test Warehouse 2 - _TC")
		
		movement2.cancel()
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "warehouse"), "_Test Warehouse - _TC")
		
		asset.load_from_db()
		asset.cancel()
		frappe.delete_doc("Asset", asset.name)
		
		
def create_asset_movement(asset, target_warehouse, transaction_date=None):
	if not transaction_date:
		transaction_date = now()
		
	movement = frappe.new_doc("Asset Movement")
	movement.update({
		"asset": asset.name,
		"transaction_date": transaction_date,
		"target_warehouse": target_warehouse,
		"company": asset.company
	})
	
	movement.insert()
	movement.submit()
	
	return movement
