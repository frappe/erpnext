import unittest

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.tests.utils import ReportFilters, ReportName, execute_script_report

EXTRA_TEST_RECORD_DEPENDENCIES = ["BOM", "Item Price", "Warehouse"]


class TestManufacturingReports(IntegrationTestCase):
	def setUp(self):
		self.setup_default_filters()

	def tearDown(self):
		frappe.db.rollback()

	def setup_default_filters(self):
		self.last_bom = frappe.get_last_doc("BOM").name
		self.DEFAULT_FILTERS = {
			"company": "_Test Company",
			"from_date": "2010-01-01",
			"to_date": "2030-01-01",
			"warehouse": "_Test Warehouse - _TC",
		}

		self.REPORT_FILTER_TEST_CASES: list[tuple[ReportName, ReportFilters]] = [
			("BOM Explorer", {"bom": self.last_bom}),
			("BOM Operations Time", {}),
			("BOM Stock Calculated", {"bom": self.last_bom, "qty_to_make": 2}),
			("BOM Stock Report", {"bom": self.last_bom, "qty_to_produce": 2}),
			("Cost of Poor Quality Report", {"item": "_Test Item", "serial_no": "00"}),
			("Downtime Analysis", {}),
			(
				"Exponential Smoothing Forecasting",
				{
					"based_on_document": "Sales Order",
					"based_on_field": "Qty",
					"no_of_years": 3,
					"periodicity": "Yearly",
					"smoothing_constant": 0.3,
				},
			),
			("Job Card Summary", {"fiscal_year": "2021-2022"}),
			("Production Analytics", {"range": "Monthly"}),
			("Quality Inspection Summary", {}),
			("Process Loss Report", {}),
			("Work Order Stock Report", {}),
			("Work Order Summary", {"fiscal_year": "2021-2022", "age": 0}),
		]

		if frappe.db.a_row_exists("Production Plan"):
			self.REPORT_FILTER_TEST_CASES.append(
				("Production Plan Summary", {"production_plan": frappe.get_last_doc("Production Plan").name})
			)

		self.OPTIONAL_FILTERS = {
			"warehouse": "_Test Warehouse - _TC",
			"item": "_Test Item",
			"item_group": "_Test Item Group",
		}

	def test_execute_all_manufacturing_reports(self):
		"""Test that all script report in manufacturing modules are executable with supported filters"""
		for report, filter in self.REPORT_FILTER_TEST_CASES:
			with self.subTest(report=report):
				execute_script_report(
					report_name=report,
					module="Manufacturing",
					filters=filter,
					default_filters=self.DEFAULT_FILTERS,
					optional_filters=self.OPTIONAL_FILTERS if filter.get("_optional") else None,
				)
