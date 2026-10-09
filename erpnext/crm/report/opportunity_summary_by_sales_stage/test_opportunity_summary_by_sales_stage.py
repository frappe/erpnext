import frappe

from erpnext.crm.report.opportunity_summary_by_sales_stage.opportunity_summary_by_sales_stage import (
	execute,
)
from erpnext.crm.report.sales_pipeline_analytics.test_sales_pipeline_analytics import (
	create_opportunity,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestOpportunitySummaryBySalesStage(ERPNextTestSuite):
	def setUp(self):
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

		expected_data = [{"utm_source": "Cold Calling", "Prospecting": 1}]

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

	def test_sales_user_can_run_the_report(self):
		from erpnext.buying.test_utils import create_user_with_roles

		user = create_user_with_roles("sales_stage_report_user@example.com", "Sales User")
		filters = {"based_on": "Opportunity Owner", "data_based_on": "Number", "company": "Best Test"}
		with self.set_user(user.name):
			columns = execute(filters)[0]

		self.assertIn("Prospecting", [column["fieldname"] for column in columns])

	def test_sales_stage_columns_follow_user_permissions(self):
		from frappe.permissions import add_user_permission

		from erpnext.buying.test_utils import create_user_with_roles

		if not frappe.db.exists("Sales Stage", "Negotiation"):
			frappe.get_doc({"doctype": "Sales Stage", "stage_name": "Negotiation"}).insert()
		user = create_user_with_roles("sales_stage_restricted_user@example.com", "Sales User")
		add_user_permission("Sales Stage", "Prospecting", user.name)
		filters = {"based_on": "Opportunity Owner", "data_based_on": "Number", "company": "Best Test"}
		with self.set_user(user.name):
			columns = execute(filters)[0]

		self.assertEqual(["Prospecting"], [column["fieldname"] for column in columns[1:]])
