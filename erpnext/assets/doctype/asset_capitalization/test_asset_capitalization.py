# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import cint, flt, getdate, now_datetime

from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries
from erpnext.assets.doctype.asset.test_asset import (
	create_asset,
	create_asset_data,
	set_depreciation_settings_in_company,
)
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
)
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	make_serial_batch_bundle,
)


class TestAssetCapitalization(IntegrationTestCase):
	def setUp(self):
		set_depreciation_settings_in_company()
		create_asset_data()
		create_asset_capitalization_data()
		frappe.db.sql("delete from `tabTax Rule`")

	def test_capitalization_with_perpetual_inventory(self):
		company = "_Test Company with perpetual inventory"
		set_depreciation_settings_in_company(company=company)
		name = frappe.db.get_value(
			"Asset Category Account",
			filters={"parent": "Computers", "company_name": company},
			fieldname=["name"],
		)
		frappe.db.set_value("Asset Category Account", name, "capital_work_in_progress_account", "")

		# Variables
		consumed_asset_value = 100000

		stock_rate = 1000
		stock_qty = 2
		stock_amount = 2000

		service_rate = 500
		service_qty = 2
		service_amount = 1000

		total_amount = 103000

		consumed_asset = create_asset(
			asset_name="Asset Capitalization Consumable Asset",
			asset_value=consumed_asset_value,
			submit=1,
			warehouse="Stores - TCP1",
			company=company,
		)

		wip_composite_asset = create_asset(
			asset_name="Asset Capitalization WIP Composite Asset",
			is_composite_asset=1,
			warehouse="Stores - TCP1",
			company=company,
		)

		# Create and submit Asset Captitalization
		asset_capitalization = create_asset_capitalization(
			target_asset=wip_composite_asset.name,
			target_asset_location="Test Location",
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
		target_asset = frappe.get_doc("Asset", asset_capitalization.target_asset)
		self.assertEqual(target_asset.net_purchase_amount, total_amount)
		self.assertEqual(target_asset.purchase_amount, total_amount)
		self.assertEqual(target_asset.status, "Work In Progress")

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

		consumed_asset = create_asset(
			asset_name="Asset Capitalization Consumable Asset",
			asset_value=consumed_asset_value,
			submit=1,
			warehouse="Stores - _TC",
			company=company,
		)

		wip_composite_asset = create_asset(
			asset_name="Asset Capitalization WIP Composite Asset",
			is_composite_asset=1,
			warehouse="Stores - TCP1",
			company=company,
		)

		# Create and submit Asset Captitalization
		asset_capitalization = create_asset_capitalization(
			target_asset=wip_composite_asset.name,
			target_asset_location="Test Location",
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
		target_asset = frappe.get_doc("Asset", asset_capitalization.target_asset)
		self.assertEqual(target_asset.net_purchase_amount, total_amount)
		self.assertEqual(target_asset.purchase_amount, total_amount)

		# Test Consumed Asset values
		self.assertEqual(consumed_asset.db_get("status"), "Capitalized")

		# Test General Ledger Entries
		default_expense_account = frappe.db.get_value("Company", company, "default_expense_account")
		expected_gle = {
			"_Test Fixed Asset - _TC": -100000.0,
			default_expense_account: -2000.0,
			"CWIP Account - _TC": 103000.0,
			"Expenses Included In Asset Valuation - _TC": -1000.0,
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

	def test_capitalization_with_wip_composite_asset(self):
		company = "_Test Company with perpetual inventory"
		set_depreciation_settings_in_company(company=company)
		name = frappe.db.get_value(
			"Asset Category Account",
			filters={"parent": "Computers", "company_name": company},
			fieldname=["name"],
		)
		frappe.db.set_value("Asset Category Account", name, "capital_work_in_progress_account", "")

		stock_rate = 1000
		stock_qty = 2
		stock_amount = 2000

		total_amount = 2000

		wip_composite_asset = create_asset(
			asset_name="Asset Capitalization WIP Composite Asset",
			is_composite_asset=1,
			warehouse="Stores - TCP1",
			company=company,
		)

		# Create and submit Asset Captitalization
		asset_capitalization = create_asset_capitalization(
			target_asset=wip_composite_asset.name,
			target_asset_location="Test Location",
			stock_qty=stock_qty,
			stock_rate=stock_rate,
			service_expense_account="Expenses Included In Asset Valuation - TCP1",
			company=company,
			submit=1,
		)

		# Test Asset Capitalization values
		self.assertEqual(asset_capitalization.target_qty, 1)

		self.assertEqual(asset_capitalization.stock_items[0].valuation_rate, stock_rate)
		self.assertEqual(asset_capitalization.stock_items[0].amount, stock_amount)
		self.assertEqual(asset_capitalization.stock_items_total, stock_amount)

		self.assertEqual(asset_capitalization.total_value, total_amount)
		self.assertEqual(asset_capitalization.target_incoming_rate, total_amount)

		# Test Target Asset values
		target_asset = frappe.get_doc("Asset", asset_capitalization.target_asset)
		self.assertEqual(target_asset.net_purchase_amount, total_amount)
		self.assertEqual(target_asset.purchase_amount, total_amount)
		self.assertEqual(target_asset.status, "Work In Progress")

		# Test General Ledger Entries
		expected_gle = {
			"_Test Fixed Asset - TCP1": 2000,
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
		self.assertFalse(get_actual_gle_dict(asset_capitalization.name))
		self.assertFalse(get_actual_sle_dict(asset_capitalization.name))

	def test_capitalize_only_service_item(self):
		company = "_Test Company"
		# Variables

		service_rate = 500
		service_qty = 2
		service_amount = 1000

		total_amount = 1000

		wip_composite_asset = create_asset(
			asset_name="Asset Capitalization WIP Composite Asset",
			is_composite_asset=1,
			warehouse="Stores - TCP1",
			company=company,
		)

		# Create and submit Asset Captitalization
		asset_capitalization = create_asset_capitalization(
			target_asset=wip_composite_asset.name,
			target_asset_location="Test Location",
			service_qty=service_qty,
			service_rate=service_rate,
			service_expense_account="Expenses Included In Asset Valuation - _TC",
			company=company,
			submit=1,
		)

		self.assertEqual(asset_capitalization.service_items[0].amount, service_amount)
		self.assertEqual(asset_capitalization.service_items_total, service_amount)

		target_asset = frappe.get_doc("Asset", asset_capitalization.target_asset)
		self.assertEqual(target_asset.net_purchase_amount, total_amount)
		self.assertEqual(target_asset.purchase_amount, total_amount)

		expected_gle = {
			"CWIP Account - _TC": 1000.0,
			"Expenses Included In Asset Valuation - _TC": -1000.0,
		}

		actual_gle = get_actual_gle_dict(asset_capitalization.name)
		self.assertEqual(actual_gle, expected_gle)

		# Cancel Asset Capitalization and make test entries and status are reversed
		asset_capitalization.cancel()
		self.assertFalse(get_actual_gle_dict(asset_capitalization.name))
		self.assertFalse(get_actual_sle_dict(asset_capitalization.name))

	def test_capitalize_composite_component(self):
		company = "_Test Company with perpetual inventory"
		set_depreciation_settings_in_company(company=company)
		name = frappe.db.get_value(
			"Asset Category Account",
			filters={"parent": "Computers", "company_name": company},
			fieldname=["name"],
		)
		frappe.db.set_value("Asset Category Account", name, "capital_work_in_progress_account", "")

		wip_composite_asset = create_asset(
			asset_name="Asset Capitalization WIP Composite Asset",
			is_composite_asset=1,
			warehouse="Stores - TCP1",
			company=company,
		)

		consumed_asset_value = 100000

		consumed_asset = create_asset(
			asset_name="Asset Capitalization Consumable Asset",
			asset_value=consumed_asset_value,
			submit=1,
			warehouse="Stores - _TC",
			is_composite_component=1,
			company=company,
		)

		# Create and submit Asset Captitalization
		asset_capitalization = create_asset_capitalization(
			target_asset=wip_composite_asset.name,
			target_asset_location="Test Location",
			consumed_asset=consumed_asset.name,
			company=company,
			submit=1,
		)

		# Test Asset Capitalization values
		self.assertEqual(asset_capitalization.target_qty, 1)
		self.assertEqual(asset_capitalization.asset_items[0].asset_value, consumed_asset_value)

		actual_gle = get_actual_gle_dict(asset_capitalization.name)
		self.assertEqual(actual_gle, {})


def create_asset_capitalization_data():
	create_item("Capitalization Target Stock Item", is_stock_item=1, is_fixed_asset=0, is_purchase_item=0)
	create_item("Capitalization Source Stock Item", is_stock_item=1, is_fixed_asset=0, is_purchase_item=0)
	create_item("Capitalization Source Service Item", is_stock_item=0, is_fixed_asset=0, is_purchase_item=0)


def create_asset_capitalization(**args):
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	args = frappe._dict(args)

	now = now_datetime()
	target_asset = frappe.get_doc("Asset", args.target_asset) if args.target_asset else frappe._dict()
	target_item_code = target_asset.item_code or args.target_item_code
	company = target_asset.company or args.company or "_Test Company"
	warehouse = args.warehouse or create_warehouse("_Test Warehouse", company=company)
	source_warehouse = args.source_warehouse or warehouse

	asset_capitalization = frappe.new_doc("Asset Capitalization")
	asset_capitalization.update(
		{
			"company": company,
			"posting_date": args.posting_date or now.strftime("%Y-%m-%d"),
			"posting_time": args.posting_time or now.strftime("%H:%M:%S.%f"),
			"target_item_code": target_item_code,
			"target_asset": target_asset.name,
			"target_asset_location": "Test Location",
			"target_qty": flt(args.target_qty) or 1,
			"target_batch_no": args.target_batch_no,
			"target_serial_no": args.target_serial_no,
			"finance_book": args.finance_book,
		}
	)

	if args.posting_date or args.posting_time:
		asset_capitalization.set_posting_time = 1

	if flt(args.stock_rate):
		bundle = None
		if args.stock_batch_no or args.stock_serial_no:
			bundle = make_serial_batch_bundle(
				frappe._dict(
					{
						"item_code": args.stock_item,
						"warehouse": source_warehouse,
						"company": frappe.get_cached_value("Warehouse", source_warehouse, "company"),
						"qty": (flt(args.stock_qty) or 1) * -1,
						"voucher_type": "Asset Capitalization",
						"type_of_transaction": "Outward",
						"serial_nos": args.stock_serial_no,
						"posting_date": asset_capitalization.posting_date,
						"posting_time": asset_capitalization.posting_time,
						"do_not_submit": True,
					}
				)
			).name

		asset_capitalization.append(
			"stock_items",
			{
				"item_code": args.stock_item or "Capitalization Source Stock Item",
				"warehouse": source_warehouse,
				"stock_qty": flt(args.stock_qty) or 1,
				"serial_and_batch_bundle": bundle,
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

	asset.net_purchase_amount = args.asset_value or 100000
	asset.purchase_amount = asset.net_purchase_amount

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
