# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import cstr, nowdate, getdate, flt, get_last_day, add_days, add_months
from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries, scrap_asset, restore_asset
from erpnext.assets.doctype.asset.asset import make_sales_invoice, make_purchase_invoice
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice as make_invoice

class TestAsset(unittest.TestCase):
	def setUp(self):
		set_depreciation_settings_in_company()
		remove_prorated_depreciation_schedule()
		create_asset_data()
		frappe.db.sql("delete from `tabTax Rule`")

	def test_purchase_asset(self):
		pr = make_purchase_receipt(item_code="Macbook Pro",
			qty=1, rate=100000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, 'name')
		asset = frappe.get_doc('Asset', asset_name)
		asset.calculate_depreciation = 1

		month_end_date = get_last_day(nowdate())
		purchase_date = nowdate() if nowdate() != month_end_date else add_days(nowdate(), -15)

		asset.available_for_use_date = purchase_date
		asset.purchase_date = purchase_date
		asset.append("finance_books", {
			"expected_value_after_useful_life": 10000,
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": month_end_date
		})
		asset.submit()

		pi = make_purchase_invoice(asset.name, asset.item_code, asset.gross_purchase_amount,
			asset.company, asset.purchase_date)
		pi.supplier = "_Test Supplier"
		pi.insert()
		pi.submit()
		asset.load_from_db()
		self.assertEqual(asset.supplier, "_Test Supplier")
		self.assertEqual(asset.purchase_date, getdate(purchase_date))
		self.assertEqual(asset.purchase_invoice, pi.name)

		expected_gle = (
			("Asset Received But Not Billed - _TC", 100000.0, 0.0),
			("Creditors - _TC", 0.0, 100000.0)
		)

		gle = frappe.db.sql("""select account, debit, credit from `tabGL Entry`
			where voucher_type='Purchase Invoice' and voucher_no = %s
			order by account""", pi.name)
		self.assertEqual(gle, expected_gle)

		pi.cancel()

		asset.load_from_db()
		self.assertEqual(asset.supplier, None)
		self.assertEqual(asset.purchase_invoice, None)

		self.assertFalse(frappe.db.get_value("GL Entry",
			{"voucher_type": "Purchase Invoice", "voucher_no": pi.name}))

	def test_is_fixed_asset_set(self):
		doc = frappe.new_doc('Purchase Invoice')
		doc.supplier = '_Test Supplier'
		doc.append('items', {
			'item_code': 'Macbook Pro',
			'qty': 1
		})

		doc.set_missing_values()
		self.assertEquals(doc.items[0].is_fixed_asset, 1)


	def test_schedule_for_straight_line_method(self):
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
		asset.save()
		self.assertEqual(asset.status, "Draft")
		expected_schedules = [
			["2020-06-06", 163.93, 163.93],
			["2021-04-06", 49836.07, 50000.0],
			["2022-02-06", 40000.0, 90000.00]
		]

		schedules = [[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in asset.get("schedules")]

		self.assertEqual(schedules, expected_schedules)

	def test_schedule_for_straight_line_method_for_existing_asset(self):
		create_asset(is_existing_asset=1)
		asset = frappe.get_doc("Asset", {"asset_name": "Macbook Pro 1"})
		asset.calculate_depreciation = 1
		asset.number_of_depreciations_booked = 1
		asset.opening_accumulated_depreciation = 40000
		asset.append("finance_books", {
			"expected_value_after_useful_life": 10000,
			"next_depreciation_date": "2020-12-31",
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": "2020-06-06"
		})
		asset.insert()
		self.assertEqual(asset.status, "Draft")
		asset.save()
		expected_schedules = [
			["2020-06-06", 197.37, 40197.37],
			["2021-04-06", 49802.63, 90000.00]
		]
		schedules = [[cstr(d.schedule_date), flt(d.depreciation_amount, 2), d.accumulated_depreciation_amount]
			for d in asset.get("schedules")]

		self.assertEqual(schedules, expected_schedules)

	def test_schedule_for_double_declining_method(self):
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
			"depreciation_method": "Double Declining Balance",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": "2020-06-06"
		})
		asset.insert()
		self.assertEqual(asset.status, "Draft")
		asset.save()

		expected_schedules = [
			["2020-06-06", 66667.0, 66667.0],
			["2021-04-06", 22222.0, 88889.0],
			["2022-02-06", 1111.0, 90000.0]
		]

		schedules = [[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in asset.get("schedules")]

		self.assertEqual(schedules, expected_schedules)

	def test_schedule_for_double_declining_method_for_existing_asset(self):
		create_asset(is_existing_asset = 1)
		asset = frappe.get_doc("Asset", {"asset_name": "Macbook Pro 1"})
		asset.calculate_depreciation = 1
		asset.is_existing_asset = 1
		asset.number_of_depreciations_booked = 1
		asset.opening_accumulated_depreciation = 50000
		asset.append("finance_books", {
			"expected_value_after_useful_life": 10000,
			"next_depreciation_date": "2020-12-31",
			"depreciation_method": "Double Declining Balance",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": "2020-06-06"
		})
		asset.insert()
		self.assertEqual(asset.status, "Draft")
		asset.save()

		asset.save()

		expected_schedules = [
			["2020-06-06", 33333.0, 83333.0],
			["2021-04-06", 6667.0, 90000.0]
		]

		schedules = [[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in asset.get("schedules")]

		self.assertEqual(schedules, expected_schedules)

	def test_schedule_for_prorated_straight_line_method(self):
		set_prorated_depreciation_schedule()
		pr = make_purchase_receipt(item_code="Macbook Pro",
			qty=1, rate=100000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, 'name')
		asset = frappe.get_doc('Asset', asset_name)
		asset.calculate_depreciation = 1
		asset.purchase_date = '2020-06-06'
		asset.is_existing_asset = 0
		asset.available_for_use_date = "2020-01-30"
		asset.append("finance_books", {
			"expected_value_after_useful_life": 10000,
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": "2020-12-31"
		})

		asset.insert()
		asset.save()

		expected_schedules = [
			["2020-12-31", 28000.0, 28000.0],
			["2021-12-31", 30000.0, 58000.0],
			["2022-12-31", 30000.0, 88000.0],
			["2023-01-30", 2000.0, 90000.0]
		]

		schedules = [[cstr(d.schedule_date), flt(d.depreciation_amount, 2), flt(d.accumulated_depreciation_amount, 2)]
			for d in asset.get("schedules")]

		self.assertEqual(schedules, expected_schedules)

		remove_prorated_depreciation_schedule()

	def test_depreciation(self):
		pr = make_purchase_receipt(item_code="Macbook Pro",
			qty=1, rate=100000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, 'name')
		asset = frappe.get_doc('Asset', asset_name)
		asset.calculate_depreciation = 1
		asset.purchase_date = '2020-06-06'
		asset.available_for_use_date = "2020-01-30"
		asset.append("finance_books", {
			"expected_value_after_useful_life": 10000,
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": "2020-12-31"
		})
		asset.insert()
		asset.submit()
		asset.load_from_db()
		self.assertEqual(asset.status, "Submitted")

		frappe.db.set_value("Company", "_Test Company", "series_for_depreciation_entry", "DEPR-")
		post_depreciation_entries(date="2021-01-01")
		asset.load_from_db()

		# check depreciation entry series
		self.assertEqual(asset.get("schedules")[0].journal_entry[:4], "DEPR")

		expected_gle = (
			("_Test Accumulated Depreciations - _TC", 0.0, 35699.15),
			("_Test Depreciations - _TC", 35699.15, 0.0)
		)

		gle = frappe.db.sql("""select account, debit, credit from `tabGL Entry`
			where against_voucher_type='Asset' and against_voucher = %s
			order by account""", asset.name)

		self.assertEqual(gle, expected_gle)
		self.assertEqual(asset.get("value_after_depreciation"), 0)

	def test_depreciation_entry_cancellation(self):
		pr = make_purchase_receipt(item_code="Macbook Pro",
			qty=1, rate=100000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, 'name')
		asset = frappe.get_doc('Asset', asset_name)
		asset.calculate_depreciation = 1
		asset.available_for_use_date = '2020-06-06'
		asset.purchase_date = '2020-06-06'
		asset.append("finance_books", {
			"expected_value_after_useful_life": 10000,
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": "2020-12-31"
		})
		asset.insert()
		asset.submit()
		post_depreciation_entries(date="2021-01-01")

		asset.load_from_db()

		# cancel depreciation entry
		depr_entry = asset.get("schedules")[0].journal_entry
		self.assertTrue(depr_entry)
		frappe.get_doc("Journal Entry", depr_entry).cancel()

		asset.load_from_db()
		depr_entry = asset.get("schedules")[0].journal_entry
		self.assertFalse(depr_entry)

	def test_scrap_asset(self):
		pr = make_purchase_receipt(item_code="Macbook Pro",
			qty=1, rate=100000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, 'name')
		asset = frappe.get_doc('Asset', asset_name)
		asset.calculate_depreciation = 1
		asset.available_for_use_date = '2020-06-06'
		asset.purchase_date = '2020-06-06'
		asset.append("finance_books", {
			"expected_value_after_useful_life": 10000,
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": "2020-06-06"
		})
		asset.insert()
		asset.submit()
		post_depreciation_entries(date="2021-01-01")

		scrap_asset(asset.name)

		asset.load_from_db()
		self.assertEqual(asset.status, "Scrapped")
		self.assertTrue(asset.journal_entry_for_scrap)

		expected_gle = (
			("_Test Accumulated Depreciations - _TC", 100000.0, 0.0),
			("_Test Fixed Asset - _TC", 0.0, 100000.0)
		)

		gle = frappe.db.sql("""select account, debit, credit from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_no = %s
			order by account""", asset.journal_entry_for_scrap)
		self.assertEqual(gle, expected_gle)

		restore_asset(asset.name)

		asset.load_from_db()
		self.assertFalse(asset.journal_entry_for_scrap)
		self.assertEqual(asset.status, "Partially Depreciated")

	def test_asset_sale(self):
		pr = make_purchase_receipt(item_code="Macbook Pro",
			qty=1, rate=100000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, 'name')
		asset = frappe.get_doc('Asset', asset_name)
		asset.calculate_depreciation = 1
		asset.available_for_use_date = '2020-06-06'
		asset.purchase_date = '2020-06-06'
		asset.append("finance_books", {
			"expected_value_after_useful_life": 10000,
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": "2020-12-31"
		})
		asset.insert()
		asset.submit()
		post_depreciation_entries(date="2021-01-01")

		si = make_sales_invoice(asset=asset.name, item_code="Macbook Pro", company="_Test Company")
		si.customer = "_Test Customer"
		si.due_date = nowdate()
		si.get("items")[0].rate = 25000
		si.insert()
		si.submit()

		self.assertEqual(frappe.db.get_value("Asset", asset.name, "status"), "Sold")

		expected_gle = (
			("_Test Accumulated Depreciations - _TC", 100000.0, 0.0),
			("_Test Fixed Asset - _TC", 0.0, 100000.0),
			("_Test Gain/Loss on Asset Disposal - _TC", 0, 25000.0),
			("Debtors - _TC", 25000.0, 0.0)
		)

		gle = frappe.db.sql("""select account, debit, credit from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no = %s
			order by account""", si.name)

		self.assertEqual(gle, expected_gle)

		si.cancel()
		frappe.delete_doc("Sales Invoice", si.name)

		self.assertEqual(frappe.db.get_value("Asset", asset.name, "status"), "Partially Depreciated")

	def test_asset_expected_value_after_useful_life(self):
		pr = make_purchase_receipt(item_code="Macbook Pro",
			qty=1, rate=100000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, 'name')
		asset = frappe.get_doc('Asset', asset_name)
		asset.calculate_depreciation = 1
		asset.available_for_use_date = '2020-06-06'
		asset.purchase_date = '2020-06-06'
		asset.append("finance_books", {
			"expected_value_after_useful_life": 10000,
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": "2020-06-06"
		})
		asset.insert()
		accumulated_depreciation_after_full_schedule = \
			max([d.accumulated_depreciation_amount for d in asset.get("schedules")])

		asset_value_after_full_schedule = (flt(asset.gross_purchase_amount) -
			flt(accumulated_depreciation_after_full_schedule))

		self.assertTrue(asset.finance_books[0].expected_value_after_useful_life >= asset_value_after_full_schedule)

	def test_cwip_accounting(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_invoice as make_purchase_invoice_from_pr)

		pr = make_purchase_receipt(item_code="Macbook Pro",
			qty=1, rate=5000, do_not_submit=True, location="Test Location")

		pr.set('taxes', [{
			'category': 'Total',
			'add_deduct_tax': 'Add',
			'charge_type': 'On Net Total',
			'account_head': '_Test Account Service Tax - _TC',
			'description': '_Test Account Service Tax',
			'cost_center': 'Main - _TC',
			'rate': 5.0
		}, {
			'category': 'Valuation and Total',
			'add_deduct_tax': 'Add',
			'charge_type': 'On Net Total',
			'account_head': '_Test Account Shipping Charges - _TC',
			'description': '_Test Account Shipping Charges',
			'cost_center': 'Main - _TC',
			'rate': 5.0
		}])

		pr.submit()

		expected_gle = (
			("Asset Received But Not Billed - _TC", 0.0, 5250.0),
			("CWIP Account - _TC", 5250.0, 0.0)
		)

		gle = frappe.db.sql("""select account, debit, credit from `tabGL Entry`
			where voucher_type='Purchase Receipt' and voucher_no = %s
			order by account""", pr.name)

		self.assertEqual(gle, expected_gle)

		pi = make_purchase_invoice_from_pr(pr.name)
		pi.submit()

		expected_gle = (
			("_Test Account Service Tax - _TC", 250.0, 0.0),
			("_Test Account Shipping Charges - _TC", 250.0, 0.0),
			("Asset Received But Not Billed - _TC", 5250.0, 0.0),
			("Creditors - _TC", 0.0, 5500.0),
			("Expenses Included In Asset Valuation - _TC", 0.0, 250.0),
		)

		gle = frappe.db.sql("""select account, debit, credit from `tabGL Entry`
			where voucher_type='Purchase Invoice' and voucher_no = %s
			order by account""", pi.name)

		self.assertEqual(gle, expected_gle)

		asset = frappe.db.get_value('Asset',
			{'purchase_receipt': pr.name, 'docstatus': 0}, 'name')

		asset_doc = frappe.get_doc('Asset', asset)

		month_end_date = get_last_day(nowdate())
		asset_doc.available_for_use_date = nowdate() if nowdate() != month_end_date else add_days(nowdate(), -15)
		self.assertEqual(asset_doc.gross_purchase_amount, 5250.0)

		asset_doc.append("finance_books", {
			"expected_value_after_useful_life": 200,
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
			"depreciation_start_date": month_end_date
		})
		asset_doc.submit()

		expected_gle = (
			("_Test Fixed Asset - _TC", 5250.0, 0.0),
			("CWIP Account - _TC", 0.0, 5250.0)
		)

		gle = frappe.db.sql("""select account, debit, credit from `tabGL Entry`
			where voucher_type='Asset' and voucher_no = %s
			order by account""", asset_doc.name)

		self.assertEqual(gle, expected_gle)

	def test_expense_head(self):
		pr = make_purchase_receipt(item_code="Macbook Pro",
			qty=2, rate=200000.0, location="Test Location")

		doc = make_invoice(pr.name)

		self.assertEquals('Asset Received But Not Billed - _TC', doc.items[0].expense_account)


def create_asset_data():
	if not frappe.db.exists("Asset Category", "Computers"):
		create_asset_category()

	if not frappe.db.exists("Item", "Macbook Pro"):
		create_fixed_asset_item()

	if not frappe.db.exists("Location", "Test Location"):
		frappe.get_doc({
			'doctype': 'Location',
			'location_name': 'Test Location'
		}).insert()

def create_asset(**args):
	args = frappe._dict(args)

	create_asset_data()

	asset = frappe.get_doc({
		"doctype": "Asset",
		"asset_name": "Macbook Pro 1",
		"asset_category": "Computers",
		"item_code": "Macbook Pro",
		"company": "_Test Company",
		"purchase_date": "2015-01-01",
		"calculate_depreciation": 0,
		"gross_purchase_amount": 100000,
		"expected_value_after_useful_life": 10000,
		"warehouse": "_Test Warehouse - _TC",
		"available_for_use_date": "2020-06-06",
		"location": "Test Location",
		"asset_owner": "Company",
		"is_existing_asset": args.is_existing_asset or 0
	})

	try:
		asset.save()
	except frappe.DuplicateEntryError:
		pass

	return asset

def create_asset_category():
	asset_category = frappe.new_doc("Asset Category")
	asset_category.asset_category_name = "Computers"
	asset_category.total_number_of_depreciations = 3
	asset_category.frequency_of_depreciation = 3
	asset_category.append("accounts", {
		"company_name": "_Test Company",
		"fixed_asset_account": "_Test Fixed Asset - _TC",
		"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
		"depreciation_expense_account": "_Test Depreciations - _TC"
	})
	asset_category.insert()

def create_fixed_asset_item():
	try:
		frappe.get_doc({
			"doctype": "Item",
			"item_code": "Macbook Pro",
			"item_name": "Macbook Pro",
			"description": "Macbook Pro Retina Display",
			"asset_category": "Computers",
			"item_group": "All Item Groups",
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_fixed_asset": 1
		}).insert()
	except frappe.DuplicateEntryError:
		pass

def set_depreciation_settings_in_company():
	company = frappe.get_doc("Company", "_Test Company")
	company.accumulated_depreciation_account = "_Test Accumulated Depreciations - _TC"
	company.depreciation_expense_account = "_Test Depreciations - _TC"
	company.disposal_account = "_Test Gain/Loss on Asset Disposal - _TC"
	company.depreciation_cost_center = "_Test Cost Center - _TC"
	company.save()

	# Enable booking asset depreciation entry automatically
	frappe.db.set_value("Accounts Settings", None, "book_asset_depreciation_entry_automatically", 1)

def remove_prorated_depreciation_schedule():
	asset_settings = frappe.get_doc("Asset Settings", "Asset Settings")
	asset_settings.schedule_based_on_fiscal_year = 0
	asset_settings.save()

	frappe.db.commit()

def set_prorated_depreciation_schedule():
	asset_settings = frappe.get_doc("Asset Settings", "Asset Settings")
	asset_settings.schedule_based_on_fiscal_year = 1
	asset_settings.number_of_days_in_fiscal_year = 360
	asset_settings.save()

	frappe.db.commit()
