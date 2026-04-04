from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.slab.api import _generate_slab_batch


class TestSlab(FrappeTestCase):
	def setUp(self):
		# Clear existing holidays to ensure deterministic tests
		frappe.db.delete("Holiday")
		frappe.db.delete("Holiday List")

		# Create a Holiday List covering the relevant dates
		self.holiday_lists = [frappe.get_doc({
			"doctype": "Holiday List",
			"holiday_list_name": "Test Holiday List 2025",
			"from_date": "2025-01-01",
			"to_date": "2025-12-31",
			"holidays": [
				{"holiday_date": "2025-12-25", "description": "Christmas"},
				{"holiday_date": "2025-01-01", "description": "New Year"}
			]
		}).insert()]

		# Create a Holiday List covering the relevant dates
		self.holiday_lists.append(frappe.get_doc({
			"doctype": "Holiday List",
			"holiday_list_name": "Test Holiday List 2026",
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
			"holidays": [
				{"holiday_date": "2026-02-25", "description": "Mahasivaratri"},
				{"holiday_date": "2026-03-02", "description": "Holi"},
				{"holiday_date": "2026-04-01", "description": "April Fools Day"},
			]
		}).insert())

		# Create a Holiday List covering the relevant dates
		self.holiday_lists.append(frappe.get_doc({
			"doctype": "Holiday List",
			"holiday_list_name": "Test Holiday List 2027",
			"from_date": "2027-01-01",
			"to_date": "2027-12-31",
			"holidays": [
				{"holiday_date": "2027-04-01", "description": "April Fools Day"},
			]
		}).insert())


		# Create a new fiscal year
		frappe.get_doc({ "doctype": "Fiscal Year",
			"year": "2026-2027",
			"year_start_date": "2026-04-01",
			"year_end_date": "2027-03-31",
		}).insert(ignore_permissions=True)


	def tearDown(self):
		frappe.db.rollback()


	@patch("erpnext.manufacturing.doctype.slab.api.date")
	def test_generate_batch_number(self, mock_date):
		# Mock today's date to 2026-03-03
		mock_date.today.return_value = date(2026, 3, 3)

		# Expected calculations for 2026-03-03:
		# today = date(2026, 3, 3)
		# year_code = chr(65 + 2026 - 2017) = 'I'
		# total_days_so_far = 336
		# curr_fin_year_start = 2025 (March is month 3 < 4)
		# year_start_date = "2025-04-01"
		# Holidays between 2025-04-01 and 2026-03-03:
		# 1. 2025-12-25 (Christmas)
		# 2. 2026-01-01 (New Year)
		# 3. 2026-02-25 (Mahasivaratri)
		# Total holidays = 3
		# total_working_days = 336 - 3 = 333
		# Result = "L1I/333"

		batch_number = _generate_slab_batch("L1")
		self.assertEqual(batch_number, "L1I/333")


	@patch("erpnext.manufacturing.doctype.slab.api.date")
	def test_generate_batch_number_with_new_fiscal_year(self, mock_date):
		# Mock today's date to 2026-04-01
		mock_date.today.return_value = date(2026, 6, 1)

		# Expected calculations for 2026-06-01:
		# today = date(2026, 6, 1)
		# year_code = chr(65 + 2026 - 2017) = 'J'
		# total_days_so_far = 30 + 31 + 0 = 61
		# curr_fin_year_start = 2027
		# year_start_date = "2026-04-01"
		# Total holidays = 1
		# total_working_days = 61 - 1 = 60
		# Result = "L1J/065"

		batch_number = _generate_slab_batch("L1")
		self.assertEqual(batch_number, "L1J/060")


	@patch("erpnext.manufacturing.doctype.slab.api.date")
	def test_generate_batch_number_with_holiday(self, mock_date):
		# Mock today's date to 2026-03-02 - A Holiday
		mock_date.today.return_value = date(2026, 3, 2)

		with self.assertRaises(frappe.exceptions.ValidationError): # The system should throw an error since the given day is a holiday.
			_generate_slab_batch("L1")


	@patch("erpnext.manufacturing.doctype.slab.api.date")
	def test_generate_batch_number_financial_year_after_april(self, mock_date):
		# Mock today's date to 2026-05-10
		mock_date.today.return_value = date(2025, 5, 10)

		# Expected calculations for 2025-05-10:
		# today = date(2025, 5, 10)
		# year_code = 'J'
		# total_days_so_far = 30+9 = 39 (since April is the start of the financial year)
		# curr_fin_year_start = 2025
		# year_start_date = "2025-04-01"

		# Add a holiday in May
		self.holiday_lists[0].append("holidays", {"holiday_date": "2025-05-01", "description": "May Day"})
		self.holiday_lists[0].save()

		# Holidays between 2025-04-01 and 2026-05-10:
		# 1. 2025-05-01
		# Total holidays = 1
		# total_working_days = 39 - 1 = 38
		# Result = "L2J/038"

		batch_number = _generate_slab_batch("L2")
		self.assertEqual(batch_number, "L2I/038")


	@patch("erpnext.manufacturing.doctype.slab.api.date")
	def test_generate_batch_number_no_fiscal_year_error(self, mock_date):
		# Mock today's date to 2024-03-03 (No holiday list for 2024)
		mock_date.today.return_value = date(2024, 3, 3)

		with self.assertRaises(frappe.exceptions.ValidationError):
			_generate_slab_batch("L1")


	@patch("erpnext.manufacturing.doctype.slab.api.date")
	def test_generate_batch_number_no_holiday_list_error(self, mock_date):
		# Mock today's date to 2024-03-03 (No holiday list for 2024)
		mock_date.today.return_value = date(2023, 3, 3)

		self.holiday_lists[0].delete()

		with self.assertRaises(frappe.exceptions.ValidationError):
			_generate_slab_batch("L1")
