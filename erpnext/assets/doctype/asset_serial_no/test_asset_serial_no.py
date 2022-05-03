# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import unittest

import frappe
from assets.asset.doctype.asset_.test_asset_ import (
	create_asset,
	create_asset_data,
	create_company,
	create_depreciation_template,
	enable_book_asset_depreciation_entry_automatically,
	enable_cwip_accounting,
	enable_finance_books,
)
from frappe.utils import getdate


class TestAssetSerialNo(unittest.TestCase):
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

	def test_num_of_asset_serial_nos_created(self):
		"""Tests if x Asset Serial Nos are created when num_of_assets = x in the Asset doc."""

		asset = create_asset(is_serialized_asset=1, num_of_assets=5, submit=1)
		asset_serial_nos = get_linked_asset_serial_nos(asset.name)

		self.assertEqual(len(asset_serial_nos), 5)

	def test_available_for_use_date_is_after_purchase_date(self):
		asset = create_asset(is_serialized_asset=1, calculate_depreciation=1, submit=1)
		asset_serial_no = get_asset_serial_no_doc(asset.name)

		asset.purchase_date = getdate("2021-10-10")
		asset_serial_no.available_for_use_date = getdate("2021-10-1")

		self.assertRaises(frappe.ValidationError, asset_serial_no.save)

	def test_depreciation_posting_start_date_and_available_for_use_date_are_not_the_same(self):
		asset = create_asset(is_serialized_asset=1, calculate_depreciation=1, submit=1)
		asset_serial_no = get_asset_serial_no_doc(asset.name)

		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2021-10-1")

		self.assertRaises(frappe.ValidationError, asset_serial_no.save)

	def test_if_depr_posting_start_date_is_too_late_when_finance_books_are_enabled(self):
		"""
		Tests if the period between Available for Use Date and Depreciation Posting Start Date
		is less than or equal to the Frequency of Depreciation.
		"""
		enable_finance_books()

		asset = create_asset(
			is_serialized_asset=1, calculate_depreciation=1, enable_finance_books=1, submit=1
		)
		asset_serial_no = get_asset_serial_no_doc(asset.name)

		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2022-11-1")

		self.assertRaises(frappe.ValidationError, asset_serial_no.save)

		enable_finance_books(enable=False)

	def test_if_depr_posting_start_date_is_too_late_when_finance_books_are_disabled(self):
		"""
		Tests if the period between Available for Use Date and Depreciation Posting Start Date
		is less than or equal to the Frequency of Depreciation.
		"""
		enable_finance_books(enable=False)

		asset = create_asset(
			is_serialized_asset=1, calculate_depreciation=1, enable_finance_books=0, submit=1
		)
		asset_serial_no = get_asset_serial_no_doc(asset.name)

		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2022-11-1")

		self.assertRaises(frappe.ValidationError, asset_serial_no.save)

	def test_if_depreciation_details_are_fetched_from_asset_category(self):
		enable_finance_books()

		asset_category = frappe.get_doc("Asset Category", "Computers")
		asset_category.append(
			"finance_books", {"depreciation_template": "Straight Line Method Annually for 5 Years"}
		)
		asset_category.save()

		asset = create_asset(
			is_serialized_asset=1, calculate_depreciation=1, enable_finance_books=1, submit=1
		)

		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2021-12-1")

		asset_serial_no.finance_books = []
		asset_serial_no.save()

		self.assertEqual(
			asset_serial_no.finance_books[0].depreciation_template,
			"Straight Line Method Annually for 5 Years",
		)

		enable_finance_books(enable=False)

	def test_depreciation_details_are_mandatory_when_finance_books_are_enabled(self):
		enable_finance_books()

		asset = create_asset(
			is_serialized_asset=1, calculate_depreciation=1, enable_finance_books=1, submit=1
		)

		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2021-12-1")

		asset_serial_no.finance_books = []

		self.assertRaises(frappe.ValidationError, asset_serial_no.save)

		enable_finance_books(enable=False)

	def test_depreciation_template_is_mandatory_when_finance_books_are_disabled(self):
		enable_finance_books(enable=False)

		asset = create_asset(
			is_serialized_asset=1, calculate_depreciation=1, enable_finance_books=0, submit=1
		)

		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2021-12-1")

		asset_serial_no.depreciation_template = None

		self.assertRaises(frappe.ValidationError, asset_serial_no.save)

	def test_missing_template_values_are_fetched_when_finance_books_are_enabled(self):
		enable_finance_books()

		asset = create_asset(
			is_serialized_asset=1, calculate_depreciation=1, enable_finance_books=1, submit=1
		)
		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2021-12-1")

		asset_serial_no.finance_books[
			0
		].depreciation_template = "Straight Line Method Annually for 5 Years"
		asset_serial_no.save()

		template_values = asset_serial_no.finance_books[0]

		self.assertEqual(template_values.depreciation_method, "Straight Line")
		self.assertEqual(template_values.frequency_of_depreciation, "Yearly")
		self.assertEqual(template_values.asset_life_in_months, 60)
		self.assertEqual(template_values.rate_of_depreciation, 0.0)

		enable_finance_books(enable=False)

	def test_missing_template_values_are_fetched_when_finance_books_are_disabled(self):
		enable_finance_books(enable=False)

		asset = create_asset(
			is_serialized_asset=1, calculate_depreciation=1, enable_finance_books=0, submit=1
		)
		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2021-12-1")

		asset_serial_no.depreciation_template = "Straight Line Method Annually for 5 Years"
		asset_serial_no.save()

		self.assertEqual(asset_serial_no.depreciation_method, "Straight Line")
		self.assertEqual(asset_serial_no.frequency_of_depreciation, "Yearly")
		self.assertEqual(asset_serial_no.asset_life_in_months, 60)
		self.assertEqual(asset_serial_no.rate_of_depreciation, 0.0)

	def test_depreciation_schedule_is_created_when_finance_books_are_enabled(self):
		enable_finance_books()

		asset = create_asset(
			is_serialized_asset=1, calculate_depreciation=1, enable_finance_books=1, submit=1
		)
		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2021-12-1")
		asset_serial_no.append(
			"finance_books", {"depreciation_template": "Straight Line Method Annually for 5 Years"}
		)
		asset_serial_no.save()

		depreciation_schedule = get_linked_depreciation_schedules(asset_serial_no.name)

		self.assertTrue(depreciation_schedule)

		enable_finance_books(enable=False)

	def test_depreciation_schedule_is_created_when_finance_books_are_disabled(self):
		enable_finance_books(enable=False)

		asset = create_asset(
			is_serialized_asset=1, calculate_depreciation=1, enable_finance_books=0, submit=1
		)
		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2021-12-1")
		asset_serial_no.depreciation_template = "Straight Line Method Annually for 5 Years"
		asset_serial_no.save()

		depreciation_schedule = get_linked_depreciation_schedules(asset_serial_no.name)

		self.assertTrue(depreciation_schedule)

	def test_new_schedules_are_created_if_basic_depr_details_are_updated(self):
		"""Tests if old schedule is deleted and new one is created on updating basic depr details."""

		asset = create_asset(is_serialized_asset=1, calculate_depreciation=1, submit=1)

		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2021-12-1")
		asset_serial_no.depreciation_template = "Straight Line Method Annually for 5 Years"
		asset_serial_no.save()

		old_depreciation_schedule = get_linked_depreciation_schedules(asset_serial_no.name)

		asset_serial_no.depreciation_posting_start_date = getdate("2021-12-15")
		asset_serial_no.save()

		new_depreciation_schedule = get_linked_depreciation_schedules(asset_serial_no.name)
		does_old_schedule_still_exist = frappe.db.exists(
			"Depreciation Schedule", old_depreciation_schedule[0]
		)

		self.assertFalse(does_old_schedule_still_exist)
		self.assertNotEqual(old_depreciation_schedule, new_depreciation_schedule)

	def test_new_schedule_is_created_on_changing_depr_template_when_finance_books_are_enabled(self):
		"""Tests if old schedule is deleted and new one is created on changing the depr template."""

		enable_finance_books()

		asset = create_asset(
			is_serialized_asset=1, calculate_depreciation=1, enable_finance_books=1, submit=1
		)

		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2021-12-1")
		asset_serial_no.append(
			"finance_books", {"depreciation_template": "Straight Line Method Annually for 5 Years"}
		)
		asset_serial_no.save()

		old_depreciation_schedule = get_linked_depreciation_schedules(asset_serial_no.name)

		new_depr_template = create_depreciation_template(
			template_name="Test Template",
			depreciation_method="Straight Line",
			frequency_of_depreciation="Yearly",
			asset_life=3,
			asset_life_unit="Years",
		)

		asset_serial_no.finance_books[0].depreciation_template = new_depr_template
		asset_serial_no.save()

		new_depreciation_schedule = get_linked_depreciation_schedules(asset_serial_no.name)
		does_old_schedule_still_exist = frappe.db.exists(
			"Depreciation Schedule", old_depreciation_schedule[0].name
		)

		self.assertFalse(does_old_schedule_still_exist)
		self.assertNotEqual(old_depreciation_schedule, new_depreciation_schedule)

		enable_finance_books(enable=False)

	def test_new_schedule_is_created_on_changing_depr_template_when_finance_books_are_disabled(self):
		"""Tests if old schedule is deleted and new one is created on changing the depr template."""

		enable_finance_books(enable=False)

		asset = create_asset(
			is_serialized_asset=1, calculate_depreciation=1, enable_finance_books=0, submit=1
		)

		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2021-12-1")
		asset_serial_no.depreciation_template = "Straight Line Method Annually for 5 Years"
		asset_serial_no.save()

		old_depreciation_schedule = get_linked_depreciation_schedules(asset_serial_no.name)

		new_depr_template = create_depreciation_template(
			template_name="Test Template",
			depreciation_method="Straight Line",
			frequency_of_depreciation="Yearly",
			asset_life=3,
			asset_life_unit="Years",
		)

		asset_serial_no.depreciation_template = new_depr_template
		asset_serial_no.save()

		new_depreciation_schedule = get_linked_depreciation_schedules(asset_serial_no.name)
		does_old_schedule_still_exist = frappe.db.exists(
			"Depreciation Schedule", old_depreciation_schedule[0].name
		)

		self.assertFalse(does_old_schedule_still_exist)
		self.assertNotEqual(old_depreciation_schedule, new_depreciation_schedule)

	def test_schedule_gets_submitted_when_asset_gets_submitted(self):
		asset = create_asset(is_serialized_asset=1, calculate_depreciation=1, submit=1)

		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.available_for_use_date = getdate("2021-10-1")
		asset_serial_no.depreciation_posting_start_date = getdate("2021-12-1")
		asset_serial_no.depreciation_template = "Straight Line Method Annually for 5 Years"
		asset_serial_no.location = "Test Location"
		asset_serial_no.save()

		depr_schedule = get_linked_depreciation_schedules(asset_serial_no.name, ["docstatus", "status"])[
			0
		]

		self.assertEqual(depr_schedule.docstatus, 0)
		self.assertEqual(depr_schedule.status, "Draft")

		asset_serial_no.submit()
		depr_schedule = get_linked_depreciation_schedules(asset_serial_no.name, ["docstatus", "status"])[
			0
		]

		self.assertEqual(depr_schedule.docstatus, 1)
		self.assertEqual(depr_schedule.status, "Active")

	def test_serial_no_creation_is_recorded(self):
		"""Tests if Asset Activity of type Creation is created on submitting an Asset Serial No."""

		asset = create_asset(is_serialized_asset=1, submit=1)

		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.location = "Test Location"
		asset_serial_no.submit()

		asset_activity = frappe.get_value(
			"Asset Activity",
			filters={"serial_no": asset_serial_no.name, "activity_type": "Creation"},
			fieldname="name",
		)

		self.assertTrue(asset_activity)

	def test_serial_no_receipt_is_recorded(self):
		"""Tests if Asset Movement of type Receipt is created on submitting an Asset Serial No."""

		asset = create_asset(is_serialized_asset=1, submit=1)

		asset_serial_no = get_asset_serial_no_doc(asset.name)
		asset_serial_no.location = "Test Location"
		asset_serial_no.submit()

		asset_movement = frappe.get_last_doc("Asset Movement")

		self.assertEqual(asset_movement.purpose, "Receipt")
		self.assertEqual(asset_movement.assets[0].asset, asset.name)
		self.assertEqual(asset_movement.assets[0].serial_no, asset_serial_no.name)

	def test_location_is_mandatory(self):
		asset = create_asset(is_serialized_asset=1, submit=1)
		asset_serial_no = get_asset_serial_no_doc(asset.name)

		self.assertRaises(frappe.ValidationError, asset_serial_no.submit)


def get_asset_serial_no_doc(asset_name):
	asset_serial_no = get_linked_asset_serial_nos(asset_name)[0]
	asset_serial_no_doc = frappe.get_doc("Asset Serial No", asset_serial_no.name)

	return asset_serial_no_doc


def get_linked_asset_serial_nos(asset_name, fields=["name"]):
	return frappe.get_all("Asset Serial No", filters={"asset": asset_name}, fields=fields)


def get_linked_depreciation_schedules(serial_no, fields=["name"]):
	return frappe.get_all("Depreciation Schedule", filters={"serial_no": serial_no}, fields=fields)
