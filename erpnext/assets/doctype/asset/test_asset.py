# Copyright (c) 2021, Ganga Manoj and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import getdate

from erpnext.assets.doctype.asset.asset import split_asset

# from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
# 	make_purchase_receipt,
# )


class TestAsset_(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()
		enable_cwip_accounting("Computers")
		enable_book_asset_depreciation_entry_automatically()
		# make_purchase_receipt(item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location")
		frappe.db.sql("delete from `tabTax Rule`")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_asset_category_is_fetched(self):
		"""Tests if the Item's Asset Category value is assigned to the Asset, if the field is empty."""

		asset = create_asset(item_code="Macbook Pro", do_not_save=1)
		asset.asset_category = None
		asset.save()

		self.assertEqual(asset.asset_category, "Computers")

	def test_gross_purchase_amount_is_mandatory(self):
		asset = create_asset(item_code="Macbook Pro", do_not_save=1)
		asset.gross_purchase_amount = 0

		self.assertRaises(frappe.MandatoryError, asset.save)

	def test_pr_or_pi_mandatory_if_not_existing_asset(self):
		"""Tests if either PI or PR is present if CWIP is enabled and is_existing_asset=0."""

		asset = create_asset(item_code="Macbook Pro", do_not_save=1)
		asset.is_existing_asset = 0

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_available_for_use_date_is_after_purchase_date(self):
		asset = create_asset(item_code="Macbook Pro", calculate_depreciation=1, do_not_save=1)
		asset.purchase_date = getdate("2021-10-10")
		asset.available_for_use_date = getdate("2021-10-1")

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_depr_posting_start_date_and_available_for_use_date_are_not_the_same(self):
		asset = create_asset(item_code="Macbook Pro", calculate_depreciation=1, do_not_save=1)
		asset.available_for_use_date = getdate("2021-10-1")
		asset.depreciation_posting_start_date = getdate("2021-10-1")

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_if_depr_posting_start_date_is_too_late_when_finance_books_are_enabled(self):
		"""
		Tests if the period between Available for Use Date and Depreciation Posting Start Date
		is less than or equal to the Frequency of Depreciation.
		"""
		enable_finance_books()

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			enable_finance_books=1,
			do_not_save=1,
		)
		asset.available_for_use_date = getdate("2021-10-1")
		asset.depreciation_posting_start_date = getdate("2022-11-1")

		self.assertRaises(frappe.ValidationError, asset.save)

		enable_finance_books(enable=False)

	def test_if_depr_posting_start_date_is_too_late_when_finance_books_are_disabled(self):
		"""
		Tests if the period between Available for Use Date and Depreciation Posting Start Date
		is less than or equal to the Frequency of Depreciation.
		"""
		enable_finance_books(enable=False)

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			enable_finance_books=0,
			do_not_save=1,
		)
		asset.available_for_use_date = getdate("2021-10-1")
		asset.depreciation_posting_start_date = getdate("2022-11-1")

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_item_exists(self):
		asset = create_asset(item_code="MacBook", do_not_save=1)

		self.assertRaises(frappe.DoesNotExistError, asset.save)

	def test_validate_item(self):
		asset = create_asset(item_code="MacBook Pro", do_not_save=1)
		item = frappe.get_doc("Item", "MacBook Pro")

		item.disabled = 1
		item.save()
		self.assertRaises(frappe.ValidationError, asset.save)
		item.disabled = 0

		item.is_fixed_asset = 0
		self.assertRaises(frappe.ValidationError, asset.save)
		item.is_fixed_asset = 1

		item.is_stock_item = 1
		self.assertRaises(frappe.ValidationError, asset.save)

	def test_num_of_assets_greater_than_zero(self):
		asset = create_asset(item_code="MacBook Pro", do_not_save=1)
		asset.num_of_assets = 0

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_asset_serial_nos_are_created(self):
		asset = create_asset(is_serialized_asset=1, num_of_assets=3, submit=1)

		serial_nos_created = frappe.get_all("Asset Serial No", filters={"asset": asset.name})

		self.assertEqual(len(serial_nos_created), 3)

	def test_if_depreciation_details_are_fetched_from_asset_category(self):
		enable_finance_books()

		asset_category = frappe.get_doc("Asset Category", "Computers")
		asset_category.append(
			"finance_books",
			{"depreciation_template": "Straight Line Method Annually for 5 Years"},
		)
		asset_category.save()

		asset = create_asset(do_not_save=1, calculate_depreciation=1)
		asset.finance_books = []
		asset.save()

		self.assertEqual(
			asset.finance_books[0].depreciation_template,
			"Straight Line Method Annually for 5 Years",
		)

		enable_finance_books(enable=False)

	def test_depreciation_template_is_mandatory_when_finance_books_are_disabled(self):
		enable_finance_books(enable=False)

		asset = create_asset(calculate_depreciation=1)
		asset.depreciation_template = None

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_depreciation_details_are_mandatory_when_finance_books_are_enabled(self):
		enable_finance_books()

		asset = create_asset(do_not_save=1, calculate_depreciation=1)
		asset.finance_books = []

		self.assertRaises(frappe.ValidationError, asset.save)

		enable_finance_books(enable=False)

	def test_missing_template_values_are_fetched_when_finance_books_are_enabled(self):
		enable_finance_books()

		asset = create_asset(calculate_depreciation=1, enable_finance_books=1)

		template_values = asset.finance_books[0]
		self.assertEqual(template_values.depreciation_method, "Straight Line")
		self.assertEqual(template_values.frequency_of_depreciation, "Yearly")
		self.assertEqual(template_values.asset_life_in_months, 60)
		self.assertEqual(template_values.rate_of_depreciation, 0.0)

		enable_finance_books(enable=False)

	def test_missing_template_values_are_fetched_when_finance_books_are_disabled(self):
		enable_finance_books(enable=False)

		asset = create_asset(calculate_depreciation=1)

		self.assertEqual(asset.depreciation_method, "Straight Line")
		self.assertEqual(asset.frequency_of_depreciation, "Yearly")
		self.assertEqual(asset.asset_life_in_months, 60)
		self.assertEqual(asset.rate_of_depreciation, 0.0)

	def test_depreciation_schedule_is_created_when_finance_books_are_enabled(self):
		enable_finance_books()

		asset = create_asset(calculate_depreciation=1, enable_finance_books=1)
		depreciation_schedule = get_linked_depreciation_schedules(asset.name)

		self.assertTrue(depreciation_schedule)

		enable_finance_books(enable=False)

	def test_depreciation_schedule_is_created_when_finance_books_are_disabled(self):
		enable_finance_books(enable=False)

		asset = create_asset(calculate_depreciation=1, enable_finance_books=0)
		depreciation_schedule = get_linked_depreciation_schedules(asset.name)

		self.assertTrue(depreciation_schedule)

	def test_new_schedules_are_created_if_basic_depr_details_are_updated(self):
		"""Tests if old schedule is deleted and new one is created on updating basic depr details."""

		asset = create_asset(calculate_depreciation=1)
		old_depreciation_schedule = get_linked_depreciation_schedules(asset.name)

		asset.gross_purchase_amount = 150000
		asset.save()

		new_depreciation_schedule = get_linked_depreciation_schedules(asset.name)
		does_old_schedule_still_exist = frappe.db.exists(
			"Depreciation Schedule", old_depreciation_schedule[0]
		)

		self.assertFalse(does_old_schedule_still_exist)
		self.assertNotEqual(old_depreciation_schedule, new_depreciation_schedule)

	def test_new_schedule_is_created_on_changing_depr_template_when_finance_books_are_enabled(
		self,
	):
		"""Tests if old schedule is deleted and new one is created on changing the depr template."""

		enable_finance_books()

		asset = create_asset(calculate_depreciation=1, enable_finance_books=1)
		old_depreciation_schedule = get_linked_depreciation_schedules(asset.name)

		new_depr_template = create_depreciation_template(
			template_name="Test Template",
			depreciation_method="Straight Line",
			frequency_of_depreciation="Yearly",
			asset_life=3,
			asset_life_unit="Years",
		)

		asset.finance_books[0].depreciation_template = new_depr_template
		asset.save()

		new_depreciation_schedule = get_linked_depreciation_schedules(asset.name)
		does_old_schedule_still_exist = frappe.db.exists(
			"Depreciation Schedule", old_depreciation_schedule[0].name
		)

		self.assertFalse(does_old_schedule_still_exist)
		self.assertNotEqual(old_depreciation_schedule, new_depreciation_schedule)

		enable_finance_books(enable=False)

	def test_new_schedule_is_created_on_changing_depr_template_when_finance_books_are_disabled(
		self,
	):
		"""Tests if old schedule is deleted and new one is created on changing the depr template."""

		enable_finance_books(enable=False)

		asset = create_asset(calculate_depreciation=1, enable_finance_books=0)
		old_depreciation_schedule = get_linked_depreciation_schedules(asset.name)

		new_depr_template = create_depreciation_template(
			template_name="Test Template",
			depreciation_method="Straight Line",
			frequency_of_depreciation="Yearly",
			asset_life=3,
			asset_life_unit="Years",
		)

		asset.depreciation_template = new_depr_template
		asset.save()

		new_depreciation_schedule = get_linked_depreciation_schedules(asset.name)
		does_old_schedule_still_exist = frappe.db.exists(
			"Depreciation Schedule", old_depreciation_schedule[0]
		)

		self.assertFalse(does_old_schedule_still_exist)
		self.assertNotEqual(old_depreciation_schedule, new_depreciation_schedule)

	def test_schedule_gets_submitted_when_asset_gets_submitted(self):
		asset = create_asset(calculate_depreciation=1)
		depr_schedule = get_linked_depreciation_schedules(asset.name, ["docstatus", "status"])[0]

		self.assertEqual(depr_schedule.docstatus, 0)
		self.assertEqual(depr_schedule.status, "Draft")

		asset.submit()
		depr_schedule = get_linked_depreciation_schedules(asset.name, ["docstatus", "status"])[0]

		self.assertEqual(depr_schedule.docstatus, 1)
		self.assertEqual(depr_schedule.status, "Active")

	def test_asset_creation_is_recorded(self):
		"""Tests if Asset Activity of type Creation is created on submitting an Asset."""

		asset = create_asset(submit=1)
		asset_activity = get_linked_asset_activity(asset.name, "Creation")

		self.assertTrue(asset_activity)

	def test_asset_receipt_is_recorded(self):
		"""Tests if Asset Movement of type Receipt is created on submitting an Asset."""

		asset = create_asset(submit=1)
		asset_movement = frappe.get_last_doc("Asset Movement")

		self.assertEqual(asset_movement.purpose, "Receipt")
		self.assertEqual(asset_movement.assets[0].asset, asset.name)

	def test_asset_split(self):
		asset = create_asset(is_serialized_asset=0, num_of_assets=5, submit=1)
		split_asset(asset, 2)

		new_asset = frappe.get_last_doc("Asset")
		asset_activity = get_linked_asset_activity(asset.name, "Split")

		self.assertEqual(new_asset.num_of_assets, 2)
		self.assertEqual(asset.num_of_assets, 3)
		self.assertTrue(asset_activity)

	def test_num_of_assets_to_be_separated_for_asset_split(self):
		"""Tests if num_of_assets_to_be_separated is less than num_of_assets in the Asset doc."""

		asset = create_asset(is_serialized_asset=0, num_of_assets=5, submit=1)
		self.assertRaises(frappe.ValidationError, split_asset, asset, 10)

	def test_copies_of_depr_schedules_are_created_during_asset_split(self):
		asset = create_asset(calculate_depreciation=1, is_serialized_asset=0, num_of_assets=5, submit=1)
		split_asset(asset, 2)

		new_asset = frappe.get_last_doc("Asset")
		schedule_linked_with_orginal_asset = get_linked_depreciation_schedules(asset.name)[0]
		schedule_linked_with_new_asset = get_linked_depreciation_schedules(
			new_asset.name, ["name", "notes"]
		)[0]

		self.assertTrue(schedule_linked_with_new_asset)
		self.assertTrue(schedule_linked_with_new_asset.notes)
		self.assertNotEqual(schedule_linked_with_orginal_asset.name, schedule_linked_with_new_asset.name)


def get_linked_depreciation_schedules(asset_name, fields=["name"]):
	return frappe.get_all("Depreciation Schedule", filters={"asset": asset_name}, fields=fields)


def get_linked_asset_activity(asset_name, activity_type):
	return frappe.get_value(
		"Asset Activity",
		filters={"asset": asset_name, "activity_type": activity_type},
		fieldname="name",
	)


def create_company():
	if not frappe.db.exists("Company", "_Test Company"):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "_Test Company",
				"country": "United States",
				"default_currency": "USD",
				"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
				"depreciation_expense_account": "_Test Depreciations - _TC",
				"disposal_account": "_Test Gain/Loss on Asset Disposal - _TC",
				"depreciation_cost_center": "_Test Cost Center - _TC",
			}
		)
		company.insert(ignore_if_duplicate=True)
	else:
		set_depreciation_settings_in_company()


def set_depreciation_settings_in_company():
	company = frappe.get_doc("Company", "_Test Company")
	company.accumulated_depreciation_account = "_Test Accumulated Depreciations - _TC"
	company.depreciation_expense_account = "_Test Depreciations - _TC"
	company.disposal_account = "_Test Gain/Loss on Asset Disposal - _TC"
	company.depreciation_cost_center = "_Test Cost Center - _TC"
	company.save()


def create_asset_data():
	if not frappe.db.exists("Asset Category", "Computers"):
		create_asset_category()

	if not frappe.db.exists("Item", "Macbook Pro"):
		create_fixed_asset_item()

	if not frappe.db.exists("Location", "Test Location"):
		create_location()

	if not frappe.db.exists("Depreciation Template", "Straight Line Method Annually for 5 Years"):
		create_depreciation_template()


def create_asset_category():
	asset_category = frappe.get_doc(
		{
			"doctype": "Asset Category",
			"asset_category_name": "Computers",
			"enable_cwip_accounting": 1,
			"accounts": [
				{
					"company_name": "_Test Company",
					"fixed_asset_account": "_Test Fixed Asset - _TC",
					"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
					"depreciation_expense_account": "_Test Depreciations - _TC",
				}
			],
		}
	)

	asset_category.insert()


def create_fixed_asset_item(item_code=None):
	naming_series = get_naming_series()

	try:
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code or "Macbook Pro",
				"item_name": "Macbook Pro",
				"description": "Macbook Pro Retina Display",
				"asset_category": "Computers",
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_naming_series": naming_series,
			}
		)
		item.insert(ignore_if_duplicate=True)
	except frappe.DuplicateEntryError:
		pass

	return item


def get_naming_series():
	meta = frappe.get_meta("Asset")
	naming_series = meta.get_field("naming_series").options.splitlines()[0] or "ACC-ASS-.YYYY.-"

	return naming_series


def create_location(location_name=None):
	frappe.get_doc(
		{"doctype": "Location", "location_name": location_name or "Test Location"}
	).insert()


def create_depreciation_template(**args):
	args = frappe._dict(args)

	depreciation_template = frappe.get_doc(
		{
			"doctype": "Depreciation Template",
			"template_name": args.template_name or "Straight Line Method Annually for 5 Years",
			"depreciation_method": args.depreciation_method or "Straight Line",
			"frequency_of_depreciation": args.frequency_of_depreciation or "Yearly",
			"asset_life": args.asset_life or 5,
			"asset_life_unit": args.asset_life_unit or "Years",
			"rate_of_depreciation": args.rate_of_depreciation or "0",
		}
	)
	depreciation_template.insert(ignore_if_duplicate=True)

	return depreciation_template.name


def enable_cwip_accounting(asset_category, enable=1):
	frappe.db.set_value("Asset Category", asset_category, "enable_cwip_accounting", enable)


def enable_book_asset_depreciation_entry_automatically():
	frappe.db.set_value("Accounts Settings", None, "book_asset_depreciation_entry_automatically", 1)


def enable_finance_books(enable=1):
	frappe.db.set_value("Accounts Settings", None, "enable_finance_books", enable)


def create_asset(**args):
	args = frappe._dict(args)

	asset = frappe.get_doc(
		{
			"doctype": "Asset",
			"asset_name": args.asset_name or "Macbook Pro 1",
			"asset_category": args.asset_category or "Computers",
			"item_code": args.item_code or "Macbook Pro",
			"num_of_assets": args.num_of_assets or 1,
			"is_serialized_asset": args.is_serialized_asset or 0,
			"asset_owner": args.asset_owner or "Company",
			"company": args.company or "_Test Company",
			"is_existing_asset": args.is_existing_asset or 1,
			"purchase_date": args.purchase_date or "2020-01-01",
			"gross_purchase_amount": args.gross_purchase_amount or 100000,
			"calculate_depreciation": args.calculate_depreciation or 0,
			"maintenance_required": args.maintenance_required or 0,
		}
	)

	if not asset.is_serialized_asset:
		asset.location = args.location or "Test Location"
		asset.custodian = args.custodian

		if asset.calculate_depreciation:
			asset.opening_accumulated_depreciation = args.opening_accumulated_depreciation or 0
			asset.available_for_use_date = args.available_for_use_date or "2020-06-06"
			asset.salvage_value = args.salvage_value or 0
			asset.depreciation_posting_start_date = args.depreciation_posting_start_date or "2021-06-06"

			if args.enable_finance_books:
				asset.append(
					"finance_books",
					{
						"finance_book": args.finance_book,
						"depreciation_template": args.depreciation_template
						or "Straight Line Method Annually for 5 Years",
					},
				)
			else:
				asset.depreciation_template = (
					args.depreciation_template or "Straight Line Method Annually for 5 Years"
				)

	if not args.do_not_save:
		try:
			asset.insert(ignore_if_duplicate=True)
		except frappe.DuplicateEntryError:
			pass

	if args.submit:
		asset.submit()

	return asset
