# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from assets.asset.doctype.asset_.test_asset_ import (
	create_asset,
	create_asset_data,
	create_company,
	enable_finance_books,
)
from frappe.utils import flt, nowdate

from erpnext.assets.doctype.asset_serial_no.test_asset_serial_no import get_asset_serial_no_doc
from erpnext.stock.doctype.item.test_item import create_item


class TestAssetRepair_(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()
		create_item("_Test Stock Item")
		frappe.db.sql("delete from `tabTax Rule`")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_asset_status_gets_updated_on_repair(self):
		asset = create_asset(submit=1)
		initial_status = asset.status
		asset_repair = create_asset_repair(asset=asset)

		if asset_repair.repair_status == "Pending":
			asset.reload()
			self.assertEqual(asset.status, "Out of Order")

		asset_repair.repair_status = "Completed"
		asset_repair.save()

		asset.reload()
		final_status = asset.status

		self.assertEqual(final_status, initial_status)

	def test_asset_serial_no_status_gets_updated_on_repair(self):
		asset = create_asset(is_serialized_asset=1, submit=1)
		asset_serial_no = get_asset_serial_no_doc(asset.name)

		initial_status = asset_serial_no.status
		asset_repair = create_asset_repair(asset=asset, asset_serial_no=asset_serial_no.name)

		if asset_repair.repair_status == "Pending":
			asset_serial_no.reload()
			self.assertEqual(asset_serial_no.status, "Out of Order")

		asset_repair.repair_status = "Completed"
		asset_repair.save()

		asset_serial_no.reload()
		final_status = asset_serial_no.status

		self.assertEqual(final_status, initial_status)

	def test_amount_calculation_for_stock_items(self):
		asset_repair = create_asset_repair(stock_consumption=1)

		for item in asset_repair.items:
			amount = flt(item.rate) * flt(item.qty)
			self.assertEqual(item.amount, amount)

	def test_total_repair_cost_calculation(self):
		asset_repair = create_asset_repair(stock_consumption=1)
		total_repair_cost = asset_repair.repair_cost

		for item in asset_repair.items:
			total_repair_cost += item.amount

		self.assertEqual(total_repair_cost, asset_repair.total_repair_cost)

	def test_repair_status_after_submit(self):
		asset_repair = create_asset_repair(submit=1)
		self.assertNotEqual(asset_repair.repair_status, "Pending")

	def test_items_are_mandatory_when_stock_consumption_is_checked(self):
		asset_repair = create_asset_repair(stock_consumption=1)
		asset_repair.items = []

		self.assertRaises(frappe.ValidationError, asset_repair.save)

	def test_warehouse_is_mandatory_when_stock_consumption_is_checked(self):
		asset_repair = create_asset_repair(stock_consumption=1)
		asset_repair.warehouse = None

		self.assertRaises(frappe.ValidationError, asset_repair.save)

	def test_stock_entry_gets_linked(self):
		"""Tests if Stock Entry gets linked when there's stock consumption."""

		asset_repair = create_asset_repair(stock_consumption=1, submit=1)
		self.assertTrue(asset_repair.stock_entry)

	def test_stock_quantity_gets_decreased(self):
		"""Tests if qty is decreased for Stock Items once they get consumed during Asset Repairs."""

		asset_repair = create_asset_repair(stock_consumption=1, submit=1)
		stock_entry = frappe.get_doc("Stock Entry", asset_repair.stock_entry)

		self.assertEqual(stock_entry.stock_entry_type, "Material Issue")
		self.assertEqual(stock_entry.items[0].s_warehouse, asset_repair.warehouse)
		self.assertEqual(stock_entry.items[0].item_code, asset_repair.items[0].item_code)
		self.assertEqual(stock_entry.items[0].qty, asset_repair.items[0].qty)

	def test_serialized_item_consumption(self):
		from erpnext.stock.doctype.serial_no.serial_no import SerialNoRequiredError
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

		stock_entry = make_serialized_item()
		serial_nos = stock_entry.get("items")[0].serial_no
		serial_no = serial_nos.split("\n")[0]

		# should not raise any error
		create_asset_repair(
			stock_consumption=1,
			item_code=stock_entry.get("items")[0].item_code,
			warehouse="_Test Warehouse - _TC",
			stock_item_serial_no=serial_no,
			submit=1,
		)

		# should raise error
		asset_repair = create_asset_repair(
			stock_consumption=1,
			warehouse="_Test Warehouse - _TC",
			item_code=stock_entry.get("items")[0].item_code,
		)
		asset_repair.repair_status = "Completed"

		self.assertRaises(SerialNoRequiredError, asset_repair.submit)

	def test_purchase_invoice_is_mandatory(self):
		asset_repair = create_asset_repair(capitalize_repair_cost=1)
		asset_repair.purchase_invoice = None

		self.assertRaises(frappe.ValidationError, asset_repair.submit)

	def test_gl_entries_are_created_on_submission(self):
		asset_repair = create_asset_repair(capitalize_repair_cost=1, submit=1)
		gl_entry = frappe.get_last_doc("GL Entry")

		self.assertEqual(asset_repair.name, gl_entry.voucher_no)

	def test_increase_in_asset_life_when_finance_books_are_disabled(self):
		enable_finance_books(enable=False)

		asset = create_asset(calculate_depreciation=1, enable_finance_books=0, submit=1)
		initial_asset_life = asset.asset_life_in_months

		create_asset_repair(asset=asset, capitalize_repair_cost=1, increase_in_asset_life=12, submit=1)
		asset.reload()

		self.assertEqual((initial_asset_life + 12), asset.asset_life_in_months)

	def test_increase_in_asset_life_when_finance_books_are_enabled(self):
		enable_finance_books()

		asset = create_asset(calculate_depreciation=1, enable_finance_books=1, submit=1)
		initial_asset_life = asset.finance_books[0].asset_life_in_months

		create_asset_repair(asset=asset, capitalize_repair_cost=1, increase_in_asset_life=12, submit=1)
		asset.reload()

		self.assertEqual((initial_asset_life + 12), asset.finance_books[0].asset_life_in_months)

		enable_finance_books(enable=False)

	def test_asset_repair_gets_recorded(self):
		asset_repair = create_asset_repair(submit=1)

		asset_activity = frappe.get_all(
			"Asset Activity", filters={"reference_docname": asset_repair.name}, fields=["activity_type"]
		)[0]

		self.assertTrue(asset_activity)
		self.assertEqual(asset_activity.activity_type, "Repair")


def create_asset_repair(**args):
	from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	args = frappe._dict(args)

	if args.asset:
		asset = args.asset
	else:
		asset = create_asset(submit=1)

	asset_repair = frappe.new_doc("Asset Repair")
	asset_repair.update(
		{
			"asset": asset.name,
			"asset_name": asset.asset_name,
			"serial_no": args.asset_serial_no,
			"num_of_assets": args.num_of_assets or (0 if args.asset_serial_no else 1),
			"failure_date": args.failure_date or nowdate(),
			"description": "Test Description",
			"repair_cost": args.repair_cost or 1000,
			"company": asset.company,
		}
	)

	if args.stock_consumption:
		asset_repair.stock_consumption = 1
		asset_repair.warehouse = args.warehouse or create_warehouse(
			"Test Warehouse", company=asset.company
		)
		asset_repair.append(
			"items",
			{
				"item_code": args.item_code or "_Test Stock Item",
				"rate": args.rate if args.get("rate") is not None else 100,
				"qty": args.qty or 1,
				"serial_no": args.stock_item_serial_no,
			},
		)

	asset_repair.insert(ignore_if_duplicate=True)

	if args.submit:
		asset_repair.repair_status = "Completed"
		asset_repair.cost_center = "_Test Cost Center - _TC"

		if args.stock_consumption:
			# since the Stock Item needs to be received before it can be issued
			stock_entry = frappe.get_doc(
				{"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": asset.company}
			)
			stock_entry.append(
				"items",
				{
					"t_warehouse": asset_repair.warehouse,
					"item_code": asset_repair.items[0].item_code,
					"qty": asset_repair.items[0].qty,
				},
			)
			stock_entry.submit()

		if args.capitalize_repair_cost:
			asset_repair.capitalize_repair_cost = 1

			if asset.calculate_depreciation:
				asset_repair.increase_in_asset_life = args.increase_in_asset_life or 12

			asset_repair.purchase_invoice = make_purchase_invoice().name

		asset_repair.submit()

	return asset_repair
