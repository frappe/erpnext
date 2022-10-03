import unittest

import frappe

from erpnext.crm.report.opportunity_summary_by_sales_stage.opportunity_summary_by_sales_stage import (
	execute,
)
from erpnext.crm.report.sales_pipeline_analytics.test_sales_pipeline_analytics import (
	create_company,
	create_customer,
	create_opportunity,
)


class TestOpportunitySummaryBySalesStage(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		frappe.db.delete("Opportunity")
		create_company()
		create_customer()
		create_opportunity()

	def test_opportunity_summary_by_sales_stage(self):
		self.check_for_opportunity_owner()
		self.check_for_source()
		self.check_for_opportunity_type()
		self.check_all_filters()

	def check_for_opportunity_owner(self):
		filters = {"based_on": "Opportunity Owner", "data_based_on": "Number", "company": "Best Test"}

		report = execute(filters)

		expected_data = [{"opportunity_owner": "Not Assigned", "Prospecting": 1}]

		self.assertEqual(expected_data, report[1])

	def check_for_source(self):
		filters = {"based_on": "Source", "data_based_on": "Number", "company": "Best Test"}

		report = execute(filters)

		expected_data = [{"source": "Cold Calling", "Prospecting": 1}]

		self.assertEqual(expected_data, report[1])

	def check_for_opportunity_type(self):
		filters = {"based_on": "Opportunity Type", "data_based_on": "Number", "company": "Best Test"}

		report = execute(filters)

		expected_data = [{"opportunity_type": "Sales", "Prospecting": 1}]

		self.assertEqual(expected_data, report[1])

	def check_all_filters(self):
		filters = {
			"based_on": "Opportunity Type",
			"data_based_on": "Number",
			"company": "Best Test",
			"opportunity_source": "Cold Calling",
			"opportunity_type": "Sales",
			"status": ["Open"],
		}

		report = execute(filters)

		expected_data = [{"opportunity_type": "Sales", "Prospecting": 1}]

		self.assertEqual(expected_data, report[1])
