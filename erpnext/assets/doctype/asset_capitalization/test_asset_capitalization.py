# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import cint, flt, getdate, now_datetime

from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries
from erpnext.assets.doctype.asset.test_asset import (
	create_asset,
	create_asset_data,
	set_depreciation_settings_in_company,
)
from erpnext.stock.doctype.item.test_item import create_item


class TestAssetCapitalization(unittest.TestCase):
	def setUp(self):
		set_depreciation_settings_in_company()
		create_asset_data()
		create_asset_capitalization_data()
		frappe.db.sql("delete from `tabTax Rule`")

	def test_capitalization_with_perpetual_inventory(self):
		company = "_Test Company with perpetual inventory"
		set_depreciation_settings_in_company(company=company)

		# Variables
		consumed_asset_value = 100000

		stock_rate = 1000
		stock_qty = 2
		stock_amount = 2000

		service_rate = 500
		service_qty = 2
		service_amount = 1000

		total_amount = 103000

		# Create assets
		target_asset = create_asset(
			asset_name="Asset Capitalization Target Asset",
			submit=1,
			warehouse="Stores - TCP1",
			company=company,
		)
		consumed_asset = create_asset(
			asset_name="Asset Capitalization Consumable Asset",
			asset_value=consumed_asset_value,
			submit=1,
			warehouse="Stores - TCP1",
			company=company,
		)

		# Create and submit Asset Captitalization
		asset_capitalization = create_asset_capitalization(
			entry_type="Capitalization",
			target_asset=target_asset.name,
			stock_qty=stock_qty,
			stock_rate=stock_rate,
			consumed_asset=consumed_asset.name,
			service_qty=service_qty,
			service_rate=service_rate,
			service_expense_account="Expenses Included In Asset Valuation - TCP1",
			company=company,
			submit=1,
		)

		# Test Asset Capitalization values
		self.assertEqual(asset_capitalization.entry_type, "Capitalization")
		self.assertEqual(asset_capitalization.target_qty, 1)

		self.assertEqual(asset_capitalization.stock_items[0].valuation_rate, stock_rate)
		self.assertEqual(asset_capitalization.stock_items[0].amount, stock_amount)
		self.assertEqual(asset_capitalization.stock_items_total, stock_amount)

		self.assertEqual(asset_capitalization.asset_items[0].asset_value, consumed_asset_value)
		self.assertEqual(asset_capitalization.asset_items_total, consumed_asset_value)

		self.assertEqual(asset_capitalization.service_items[0].amount, service_amount)
		self.assertEqual(asset_capitalization.service_items_total, service_amount)

		self.assertEqual(asset_capitalization.total_value, total_amount)
		self.assertEqual(asset_capitalization.target_incoming_rate, total_amount)

		# Test Target Asset values
		target_asset.reload()
		self.assertEqual(target_asset.gross_purchase_amount, total_amount)
		self.assertEqual(target_asset.purchase_receipt_amount, total_amount)

		# Test Consumed Asset values
		self.assertEqual(consumed_asset.db_get("status"), "Capitalized")

		# Test General Ledger Entries
		expected_gle = {
			"_Test Fixed Asset - TCP1": 3000,
			"Expenses Included In Asset Valuation - TCP1": -1000,
			"_Test Warehouse - TCP1": -2000,
		}
		actual_gle = get_actual_gle_dict(asset_capitalization.name)

		self.assertEqual(actual_gle, expected_gle)

		# Test Stock Ledger Entries
		expected_sle = {
			("Capitalization Source Stock Item", "_Test Warehouse - TCP1"): {
				"actual_qty": -stock_qty,
				"stock_value_difference": -stock_amount,
			}
		}
		actual_sle = get_actual_sle_dict(asset_capitalization.name)
		self.assertEqual(actual_sle, expected_sle)

		# Cancel Asset Capitalization and make test entries and status are reversed
		asset_capitalization.cancel()
		self.assertEqual(consumed_asset.db_get("status"), "Submitted")
		self.assertFalse(get_actual_gle_dict(asset_capitalization.name))
		self.assertFalse(get_actual_sle_dict(asset_capitalization.name))

	def test_capitalization_with_periodical_inventory(self):
		company = "_Test Company"
		# Variables
		consumed_asset_value = 100000

		stock_rate = 1000
		stock_qty = 2
		stock_amount = 2000

		service_rate = 500
		service_qty = 2
		service_amount = 1000

		total_amount = 103000

		# Create assets
		target_asset = create_asset(
			asset_name="Asset Capitalization Target Asset",
			submit=1,
			warehouse="Stores - _TC",
			company=company,
		)
		consumed_asset = create_asset(
			asset_name="Asset Capitalization Consumable Asset",
			asset_value=consumed_asset_value,
			submit=1,
			warehouse="Stores - _TC",
			company=company,
		)

		# Create and submit Asset Captitalization
		asset_capitalization = create_asset_capitalization(
			entry_type="Capitalization",
			target_asset=target_asset.name,
			stock_qty=stock_qty,
			stock_rate=stock_rate,
			consumed_asset=consumed_asset.name,
			service_qty=service_qty,
			service_rate=service_rate,
			service_expense_account="Expenses Included In Asset Valuation - _TC",
			company=company,
			submit=1,
		)

		# Test Asset Capitalization values
		self.assertEqual(asset_capitalization.entry_type, "Capitalization")
		self.assertEqual(asset_capitalization.target_qty, 1)

		self.assertEqual(asset_capitalization.stock_items[0].valuation_rate, stock_rate)
		self.assertEqual(asset_capitalization.stock_items[0].amount, stock_amount)
		self.assertEqual(asset_capitalization.stock_items_total, stock_amount)

		self.assertEqual(asset_capitalization.asset_items[0].asset_value, consumed_asset_value)
		self.assertEqual(asset_capitalization.asset_items_total, consumed_asset_value)

		self.assertEqual(asset_capitalization.service_items[0].amount, service_amount)
		self.assertEqual(asset_capitalization.service_items_total, service_amount)

		self.assertEqual(asset_capitalization.total_value, total_amount)
		self.assertEqual(asset_capitalization.target_incoming_rate, total_amount)

		# Test Target Asset values
		target_asset.reload()
		self.assertEqual(target_asset.gross_purchase_amount, total_amount)
		self.assertEqual(target_asset.purchase_receipt_amount, total_amount)

		# Test Consumed Asset values
		self.assertEqual(consumed_asset.db_get("status"), "Capitalized")

		# Test General Ledger Entries
		default_expense_account = frappe.db.get_value("Company", company, "default_expense_account")
		expected_gle = {
			"_Test Fixed Asset - _TC": 3000,
			"Expenses Included In Asset Valuation - _TC": -1000,
			default_expense_account: -2000,
		}
		actual_gle = get_actual_gle_dict(asset_capitalization.name)

		self.assertEqual(actual_gle, expected_gle)

		# Test Stock Ledger Entries
		expected_sle = {
			("Capitalization Source Stock Item", "_Test Warehouse - _TC"): {
				"actual_qty": -stock_qty,
				"stock_value_difference": -stock_amount,
			}
		}
		actual_sle = get_actual_sle_dict(asset_capitalization.name)
		self.assertEqual(actual_sle, expected_sle)

		# Cancel Asset Capitalization and make test entries and status are reversed
		asset_capitalization.cancel()
		self.assertEqual(consumed_asset.db_get("status"), "Submitted")
		self.assertFalse(get_actual_gle_dict(asset_capitalization.name))
		self.assertFalse(get_actual_sle_dict(asset_capitalization.name))

	def test_decapitalization_with_depreciation(self):
		# Variables
		purchase_date = "2020-01-01"
		depreciation_start_date = "2020-12-31"
		capitalization_date = "2021-06-30"

		total_number_of_depreciations = 3
		expected_value_after_useful_life = 10_000
		consumed_asset_purchase_value = 100_000
		consumed_asset_current_value = 70_000
		consumed_asset_value_before_disposal = 55_000

		target_qty = 10
		target_incoming_rate = 5500

		depreciation_before_disposal_amount = 15_000
		accumulated_depreciation = 45_000

		# to accomodate for depreciation on disposal calculation minor difference
		consumed_asset_value_before_disposal = 55_123.29
		target_incoming_rate = 5512.329
		depreciation_before_disposal_amount = 14_876.71
		accumulated_depreciation = 44_876.71

		# Create assets
		consumed_asset = create_depreciation_asset(
			asset_name="Asset Capitalization Consumable Asset",
			asset_value=consumed_asset_purchase_value,
			purchase_date=purchase_date,
			depreciation_start_date=depreciation_start_date,
			depreciation_method="Straight Line",
			total_number_of_depreciations=total_number_of_depreciations,
			frequency_of_depreciation=12,
			expected_value_after_useful_life=expected_value_after_useful_life,
			company="_Test Company with perpetual inventory",
			submit=1,
		)

		# Create and submit Asset Captitalization
		asset_capitalization = create_asset_capitalization(
			entry_type="Decapitalization",
			posting_date=capitalization_date,  # half a year
			target_item_code="Capitalization Target Stock Item",
			target_qty=target_qty,
			consumed_asset=consumed_asset.name,
			company="_Test Company with perpetual inventory",
			submit=1,
		)

		# Test Asset Capitalization values
		self.assertEqual(asset_capitalization.entry_type, "Decapitalization")

		self.assertEqual(
			asset_capitalization.asset_items[0].current_asset_value, consumed_asset_current_value
		)
		self.assertEqual(
			asset_capitalization.asset_items[0].asset_value, consumed_asset_value_before_disposal
		)
		self.assertEqual(asset_capitalization.asset_items_total, consumed_asset_value_before_disposal)

		self.assertEqual(asset_capitalization.total_value, consumed_asset_value_before_disposal)
		self.assertEqual(asset_capitalization.target_incoming_rate, target_incoming_rate)

		# Test Consumed Asset values
		consumed_asset.reload()
		self.assertEqual(consumed_asset.status, "Decapitalized")

		consumed_depreciation_schedule = [
			d for d in consumed_asset.schedules if getdate(d.schedule_date) == getdate(capitalization_date)
		]
		self.assertTrue(
			consumed_depreciation_schedule and consumed_depreciation_schedule[0].journal_entry
		)
		self.assertEqual(
			consumed_depreciation_schedule[0].depreciation_amount, depreciation_before_disposal_amount
		)

		# Test General Ledger Entries
		expected_gle = {
			"_Test Warehouse - TCP1": consumed_asset_value_before_disposal,
			"_Test Accumulated Depreciations - TCP1": accumulated_depreciation,
			"_Test Fixed Asset - TCP1": -consumed_asset_purchase_value,
		}
		actual_gle = get_actual_gle_dict(asset_capitalization.name)
		self.assertEqual(actual_gle, expected_gle)

		# Cancel Asset Capitalization and make test entries and status are reversed
		asset_capitalization.reload()
		asset_capitalization.cancel()
		self.assertEqual(consumed_asset.db_get("status"), "Partially Depreciated")
		self.assertFalse(get_actual_gle_dict(asset_capitalization.name))
		self.assertFalse(get_actual_sle_dict(asset_capitalization.name))


def create_asset_capitalization_data():
	create_item(
		"Capitalization Target Stock Item", is_stock_item=1, is_fixed_asset=0, is_purchase_item=0
	)
	create_item(
		"Capitalization Source Stock Item", is_stock_item=1, is_fixed_asset=0, is_purchase_item=0
	)
	create_item(
		"Capitalization Source Service Item", is_stock_item=0, is_fixed_asset=0, is_purchase_item=0
	)


def create_asset_capitalization(**args):
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	args = frappe._dict(args)

	now = now_datetime()
	target_asset = frappe.get_doc("Asset", args.target_asset) if args.target_asset else frappe._dict()
	target_item_code = target_asset.item_code or args.target_item_code
	company = target_asset.company or args.company or "_Test Company"
	warehouse = args.warehouse or create_warehouse("_Test Warehouse", company=company)
	target_warehouse = args.target_warehouse or warehouse
	source_warehouse = args.source_warehouse or warehouse

	asset_capitalization = frappe.new_doc("Asset Capitalization")
	asset_capitalization.update(
		{
			"entry_type": args.entry_type or "Capitalization",
			"company": company,
			"posting_date": args.posting_date or now.strftime("%Y-%m-%d"),
			"posting_time": args.posting_time or now.strftime("%H:%M:%S.%f"),
			"target_item_code": target_item_code,
			"target_asset": target_asset.name,
			"target_warehouse": target_warehouse,
			"target_qty": flt(args.target_qty) or 1,
			"target_batch_no": args.target_batch_no,
			"target_serial_no": args.target_serial_no,
			"finance_book": args.finance_book,
		}
	)

	if args.posting_date or args.posting_time:
		asset_capitalization.set_posting_time = 1

	if flt(args.stock_rate):
		asset_capitalization.append(
			"stock_items",
			{
				"item_code": args.stock_item or "Capitalization Source Stock Item",
				"warehouse": source_warehouse,
				"stock_qty": flt(args.stock_qty) or 1,
				"batch_no": args.stock_batch_no,
				"serial_no": args.stock_serial_no,
			},
		)

	if args.consumed_asset:
		asset_capitalization.append(
			"asset_items",
			{
				"asset": args.consumed_asset,
			},
		)

	if flt(args.service_rate):
		asset_capitalization.append(
			"service_items",
			{
				"item_code": args.service_item or "Capitalization Source Service Item",
				"expense_account": args.service_expense_account,
				"qty": flt(args.service_qty) or 1,
				"rate": flt(args.service_rate),
			},
		)

	if args.submit:
		create_stock_reconciliation(asset_capitalization, stock_rate=args.stock_rate)

	asset_capitalization.insert()

	if args.submit:
		asset_capitalization.submit()

	return asset_capitalization


def create_stock_reconciliation(asset_capitalization, stock_rate=0):
	from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
		EmptyStockReconciliationItemsError,
		create_stock_reconciliation,
	)

	if not asset_capitalization.get("stock_items"):
		return

	try:
		create_stock_reconciliation(
			item_code=asset_capitalization.stock_items[0].item_code,
			warehouse=asset_capitalization.stock_items[0].warehouse,
			qty=flt(asset_capitalization.stock_items[0].stock_qty),
			rate=flt(stock_rate),
			company=asset_capitalization.company,
		)
	except EmptyStockReconciliationItemsError:
		pass


def create_depreciation_asset(**args):
	args = frappe._dict(args)

	asset = frappe.new_doc("Asset")
	asset.is_existing_asset = 1
	asset.calculate_depreciation = 1
	asset.asset_owner = "Company"

	asset.company = args.company or "_Test Company"
	asset.item_code = args.item_code or "Macbook Pro"
	asset.asset_name = args.asset_name or asset.item_code
	asset.location = args.location or "Test Location"

	asset.purchase_date = args.purchase_date or "2020-01-01"
	asset.available_for_use_date = args.available_for_use_date or asset.purchase_date

	asset.gross_purchase_amount = args.asset_value or 100000
	asset.purchase_receipt_amount = asset.gross_purchase_amount

	finance_book = asset.append("finance_books")
	finance_book.depreciation_start_date = args.depreciation_start_date or "2020-12-31"
	finance_book.depreciation_method = args.depreciation_method or "Straight Line"
	finance_book.total_number_of_depreciations = cint(args.total_number_of_depreciations) or 3
	finance_book.frequency_of_depreciation = cint(args.frequency_of_depreciation) or 12
	finance_book.expected_value_after_useful_life = flt(args.expected_value_after_useful_life)

	if args.submit:
		asset.submit()

		frappe.db.set_value("Company", "_Test Company", "series_for_depreciation_entry", "DEPR-")
		post_depreciation_entries(date=finance_book.depreciation_start_date)
		asset.load_from_db()

	return asset


def get_actual_gle_dict(name):
	return dict(
		frappe.db.sql(
			"""
		select account, sum(debit-credit) as diff
		from `tabGL Entry`
		where voucher_type = 'Asset Capitalization' and voucher_no = %s
		group by account
		having diff != 0
	""",
			name,
		)
	)


def get_actual_sle_dict(name):
	sles = frappe.db.sql(
		"""
		select
			item_code, warehouse,
			sum(actual_qty) as actual_qty,
			sum(stock_value_difference) as stock_value_difference
		from `tabStock Ledger Entry`
		where voucher_type = 'Asset Capitalization' and voucher_no = %s
		group by item_code, warehouse
		having actual_qty != 0
	""",
		name,
		as_dict=1,
	)

	sle_dict = {}
	for d in sles:
		sle_dict[(d.item_code, d.warehouse)] = {
			"actual_qty": d.actual_qty,
			"stock_value_difference": d.stock_value_difference,
		}

	return sle_dict
