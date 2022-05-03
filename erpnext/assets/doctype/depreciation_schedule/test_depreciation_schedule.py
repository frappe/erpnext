# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

import unittest

import frappe
from frappe.utils import getdate

from erpnext.assets.doctype.asset.test_asset import (
	create_asset,
	create_asset_data,
	create_company,
	create_depreciation_template,
	enable_book_asset_depreciation_entry_automatically,
	enable_finance_books,
	get_linked_depreciation_schedules,
)


class TestDepreciationSchedule(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()
		create_standard_depreciation_templates()
		enable_book_asset_depreciation_entry_automatically()
		# make_purchase_receipt(item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location")
		frappe.db.sql("delete from `tabTax Rule`")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_depr_schedules_are_created_for_slm_when_fb_are_disabled(self):
		"""Tests Straight Line Method of depreciation when Finance Books are disabled."""

		enable_finance_books(enable=False)

		asset = create_asset(
			gross_purchase_amount=10000,
			calculate_depreciation=1,
			enable_finance_books=0,
			depreciation_template="Test SLM Template",
		)

		depr_schedule = get_linked_depreciation_schedules(asset.name)[0]
		depr_schedule = frappe.get_doc("Depreciation Schedule", depr_schedule["name"])

		expected_results = [
			["2021-06-06", 3342.465753425, 3342.465753425],
			["2022-06-06", 3333.333333333, 6675.799086758],
			["2023-06-06", 3333.333333333, 10009.132420091],
		]

		self.compare_depr_schedules(depr_schedule.depreciation_schedule, expected_results)

	def compare_depr_schedules(self, schedules, expected_results):
		for i, schedule in enumerate(schedules):
			self.assertEqual(schedule.schedule_date, getdate(expected_results[i][0]))
			self.assertEqual(schedule.depreciation_amount, expected_results[i][1])
			self.assertEqual(schedule.accumulated_depreciation_amount, expected_results[i][2])


def create_standard_depreciation_templates():
	create_depreciation_template(
		template_name="Test SLM Template",
		depreciation_method="Straight Line",
		frequency_of_depreciation="Yearly",
		asset_life=3,
		asset_life_unit="Years",
	)
