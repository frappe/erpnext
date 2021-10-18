# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from frappe.utils import flt, nowdate

from erpnext.assets.doctype.asset.test_asset import (
	create_asset,
	create_asset_data,
	set_depreciation_settings_in_company,
)


class TestAssetRepair(unittest.TestCase):
	def setUp(self):
		set_depreciation_settings_in_company()
		create_asset_data()
		frappe.db.sql("delete from `tabTax Rule`")

	def test_update_status(self):
		asset = create_asset(submit=1)
		initial_status = asset.status
		asset_repair = create_asset_repair(asset = asset)

		if asset_repair.repair_status == "Pending":
			asset.reload()
			self.assertEqual(asset.status, "Out of Order")

		asset_repair.repair_status = "Completed"
		asset_repair.save()
		asset_status = frappe.db.get_value("Asset", asset_repair.asset, "status")
		self.assertEqual(asset_status, initial_status)

	def test_stock_item_total_value(self):
		asset_repair = create_asset_repair(stock_consumption = 1)

		for item in asset_repair.stock_items:
			total_value = flt(item.valuation_rate) * flt(item.consumed_quantity)
			self.assertEqual(item.total_value, total_value)

	def test_total_repair_cost(self):
		asset_repair = create_asset_repair(stock_consumption = 1)

		total_repair_cost = asset_repair.repair_cost
		self.assertEqual(total_repair_cost, asset_repair.repair_cost)
		for item in asset_repair.stock_items:
			total_repair_cost += item.total_value

		self.assertEqual(total_repair_cost, asset_repair.total_repair_cost)

	def test_repair_status_after_submit(self):
		asset_repair = create_asset_repair(submit = 1)
		self.assertNotEqual(asset_repair.repair_status, "Pending")

	def test_stock_items(self):
		asset_repair = create_asset_repair(stock_consumption = 1)
		self.assertTrue(asset_repair.stock_consumption)
		self.assertTrue(asset_repair.stock_items)

	def test_warehouse(self):
		asset_repair = create_asset_repair(stock_consumption = 1)
		self.assertTrue(asset_repair.stock_consumption)
		self.assertTrue(asset_repair.warehouse)

	def test_decrease_stock_quantity(self):
		asset_repair = create_asset_repair(stock_consumption = 1, submit = 1)
		stock_entry = frappe.get_last_doc('Stock Entry')

		self.assertEqual(stock_entry.stock_entry_type, "Material Issue")
		self.assertEqual(stock_entry.items[0].s_warehouse, asset_repair.warehouse)
		self.assertEqual(stock_entry.items[0].item_code, asset_repair.stock_items[0].item)
		self.assertEqual(stock_entry.items[0].qty, asset_repair.stock_items[0].consumed_quantity)

	def test_increase_in_asset_value_due_to_stock_consumption(self):
		asset = create_asset(calculate_depreciation = 1, submit=1)
		initial_asset_value = get_asset_value(asset)
		asset_repair = create_asset_repair(asset= asset, stock_consumption = 1, submit = 1)
		asset.reload()

		increase_in_asset_value = get_asset_value(asset) - initial_asset_value
		self.assertEqual(asset_repair.stock_items[0].total_value, increase_in_asset_value)

	def test_increase_in_asset_value_due_to_repair_cost_capitalisation(self):
		asset = create_asset(calculate_depreciation = 1, submit=1)
		initial_asset_value = get_asset_value(asset)
		asset_repair = create_asset_repair(asset= asset, capitalize_repair_cost = 1, submit = 1)
		asset.reload()

		increase_in_asset_value = get_asset_value(asset) - initial_asset_value
		self.assertEqual(asset_repair.repair_cost, increase_in_asset_value)

	def test_purchase_invoice(self):
		asset_repair = create_asset_repair(capitalize_repair_cost = 1, submit = 1)
		self.assertTrue(asset_repair.purchase_invoice)

	def test_gl_entries(self):
		asset_repair = create_asset_repair(capitalize_repair_cost = 1, submit = 1)
		gl_entry = frappe.get_last_doc('GL Entry')
		self.assertEqual(asset_repair.name, gl_entry.voucher_no)

	def test_increase_in_asset_life(self):
		asset = create_asset(calculate_depreciation = 1, submit=1)
		initial_num_of_depreciations = num_of_depreciations(asset)
		create_asset_repair(asset= asset, capitalize_repair_cost = 1, submit = 1)
		asset.reload()

		self.assertEqual((initial_num_of_depreciations + 1), num_of_depreciations(asset))
		self.assertEqual(asset.schedules[-1].accumulated_depreciation_amount, asset.finance_books[0].value_after_depreciation)

def get_asset_value(asset):
	return asset.finance_books[0].value_after_depreciation

def num_of_depreciations(asset):
	return asset.finance_books[0].total_number_of_depreciations

def create_asset_repair(**args):
	from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	args = frappe._dict(args)

	if args.asset:
		asset = args.asset
	else:
		asset = create_asset(is_existing_asset = 1, submit=1)
	asset_repair = frappe.new_doc("Asset Repair")
	asset_repair.update({
		"asset": asset.name,
		"asset_name": asset.asset_name,
		"failure_date": nowdate(),
		"description": "Test Description",
		"repair_cost": 0,
		"company": asset.company
	})

	if args.stock_consumption:
		asset_repair.stock_consumption = 1
		asset_repair.warehouse = create_warehouse("Test Warehouse", company = asset.company)
		asset_repair.append("stock_items", {
			"item": args.item or args.item_code or "_Test Item",
			"valuation_rate": args.rate if args.get("rate") is not None else 100,
			"consumed_quantity": args.qty or 1
		})

	asset_repair.insert(ignore_if_duplicate=True)

	if args.submit:
		asset_repair.repair_status = "Completed"
		asset_repair.cost_center = "_Test Cost Center - _TC"

		if args.stock_consumption:
			stock_entry = frappe.get_doc({
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": asset.company
			})
			stock_entry.append('items', {
				"t_warehouse": asset_repair.warehouse,
				"item_code": asset_repair.stock_items[0].item,
				"qty": asset_repair.stock_items[0].consumed_quantity
			})
			stock_entry.submit()

		if args.capitalize_repair_cost:
			asset_repair.capitalize_repair_cost = 1
			asset_repair.repair_cost = 1000
			if asset.calculate_depreciation:
				asset_repair.increase_in_asset_life = 12
			asset_repair.purchase_invoice = make_purchase_invoice().name

		asset_repair.submit()
	return asset_repair
