import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import today

from erpnext.crm.report.sales_pipeline_analytics.sales_pipeline_analytics import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestSalesPipelineAnalytics(ERPNextTestSuite):
	def setUp(self):
		create_opportunity()

	def test_sales_pipeline_analytics(self):
		self.from_date = "2021-01-01"
		self.to_date = "2021-12-31"
		self.check_for_monthly_and_number()
		self.check_for_monthly_and_amount()
		self.check_for_quarterly_and_number()
		self.check_for_quarterly_and_amount()
		self.check_for_all_filters()

	def check_for_monthly_and_number(self):
		filters = {
			"pipeline_by": "Owner",
			"range": "Monthly",
			"based_on": "Number",
			"status": "Open",
			"opportunity_type": "Sales",
			"company": "Best Test",
			"from_date": self.from_date,
			"to_date": self.to_date,
		}

		report = execute(filters)

		expected_data = [{"opportunity_owner": "Not Assigned", "august_2021": 1}]

		self.assertEqual(expected_data, report[1])

		filters = {
			"pipeline_by": "Sales Stage",
			"range": "Monthly",
			"based_on": "Number",
			"status": "Open",
			"opportunity_type": "Sales",
			"company": "Best Test",
			"from_date": self.from_date,
			"to_date": self.to_date,
		}

		report = execute(filters)

		expected_data = [{"sales_stage": "Prospecting", "august_2021": 1}]

		self.assertEqual(expected_data, report[1])

	def check_for_monthly_and_amount(self):
		filters = {
			"pipeline_by": "Owner",
			"range": "Monthly",
			"based_on": "Amount",
			"status": "Open",
			"opportunity_type": "Sales",
			"company": "Best Test",
			"from_date": self.from_date,
			"to_date": self.to_date,
		}

		report = execute(filters)

		expected_data = [{"opportunity_owner": "Not Assigned", "august_2021": 150000}]

		self.assertEqual(expected_data, report[1])

		filters = {
			"pipeline_by": "Sales Stage",
			"range": "Monthly",
			"based_on": "Amount",
			"status": "Open",
			"opportunity_type": "Sales",
			"company": "Best Test",
			"from_date": self.from_date,
			"to_date": self.to_date,
		}

		report = execute(filters)

		expected_data = [{"sales_stage": "Prospecting", "august_2021": 150000}]

		self.assertEqual(expected_data, report[1])

	def check_for_quarterly_and_number(self):
		filters = {
			"pipeline_by": "Owner",
			"range": "Quarterly",
			"based_on": "Number",
			"status": "Open",
			"opportunity_type": "Sales",
			"company": "Best Test",
			"from_date": self.from_date,
			"to_date": self.to_date,
		}

		report = execute(filters)

		expected_data = [{"opportunity_owner": "Not Assigned", "q3_2021": 1}]

		self.assertEqual(expected_data, report[1])

		filters = {
			"pipeline_by": "Sales Stage",
			"range": "Quarterly",
			"based_on": "Number",
			"status": "Open",
			"opportunity_type": "Sales",
			"company": "Best Test",
			"from_date": self.from_date,
			"to_date": self.to_date,
		}

		report = execute(filters)

		expected_data = [{"sales_stage": "Prospecting", "q3_2021": 1}]

		self.assertEqual(expected_data, report[1])

	def check_for_quarterly_and_amount(self):
		filters = {
			"pipeline_by": "Owner",
			"range": "Quarterly",
			"based_on": "Amount",
			"status": "Open",
			"opportunity_type": "Sales",
			"company": "Best Test",
			"from_date": self.from_date,
			"to_date": self.to_date,
		}

		report = execute(filters)

		expected_data = [{"opportunity_owner": "Not Assigned", "q3_2021": 150000}]

		self.assertEqual(expected_data, report[1])

		filters = {
			"pipeline_by": "Sales Stage",
			"range": "Quarterly",
			"based_on": "Amount",
			"status": "Open",
			"opportunity_type": "Sales",
			"company": "Best Test",
			"from_date": self.from_date,
			"to_date": self.to_date,
		}

		report = execute(filters)

		expected_data = [{"sales_stage": "Prospecting", "q3_2021": 150000}]

		self.assertEqual(expected_data, report[1])

	def check_for_all_filters(self):
		filters = {
			"pipeline_by": "Owner",
			"range": "Monthly",
			"based_on": "Number",
			"status": "Open",
			"opportunity_type": "Sales",
			"company": "Best Test",
			"opportunity_source": "Cold Calling",
			"from_date": self.from_date,
			"to_date": self.to_date,
		}

		report = execute(filters)

		expected_data = [{"opportunity_owner": "Not Assigned", "august_2021": 1}]

		self.assertEqual(expected_data, report[1])

	def test_amount_uses_opportunity_conversion_rate(self):
		stage = make_sales_stage()
		frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": today(),
				"from_currency": "USD",
				"to_currency": "INR",
				"exchange_rate": 90,
			}
		).insert(ignore_if_duplicate=True)
		make_stage_opportunity(stage, 1000, "2026-01-20")
		make_stage_opportunity(stage, 100, "2026-01-25", currency="USD", conversion_rate=80)

		rows = stage_rows(stage, based_on="Amount", from_date="2026-01-01", to_date="2026-01-31")

		self.assertEqual(rows[0]["january_2026"], 9000)

		# amounts of companies with different currencies can't be added together
		with self.assertRaises(frappe.ValidationError):
			stage_rows(stage, based_on="Amount", company=None, from_date="2026-01-01", to_date="2026-01-31")

	def test_periods_of_different_years(self):
		stage = make_sales_stage()
		make_stage_opportunity(stage, 500, "2025-01-10")
		make_stage_opportunity(stage, 1000, "2026-01-20")
		make_stage_opportunity(stage, 300, "2026-02-05")

		rows = stage_rows(stage, from_date="2025-01-01", to_date="2026-02-28")
		self.assertEqual(rows[0]["january_2025"], 1)
		self.assertEqual(rows[0]["january_2026"], 1)

		rows = stage_rows(
			stage, based_on="Amount", range="Quarterly", from_date="2025-01-01", to_date="2026-03-31"
		)
		self.assertEqual(rows[0]["q1_2025"], 500)
		self.assertEqual(rows[0]["q1_2026"], 1300)

	def test_last_month_shown_when_to_date_is_earlier_in_its_month(self):
		stage = make_sales_stage()
		make_stage_opportunity(stage, 300, "2026-02-05")

		columns, data = execute(stage_filters(from_date="2026-01-15", to_date="2026-02-10"))[:2]

		self.assertIn("february_2026", [column["fieldname"] for column in columns])

	def test_territory_restricted_user_sees_only_permitted_opportunities(self):
		stage = make_sales_stage()
		make_stage_opportunity(stage, 100, "2026-01-20", territory="_Test Territory India")
		make_stage_opportunity(stage, 100, "2026-01-20", territory="_Test Territory Rest Of The World")
		user = create_user("pipeline_territory_user@example.com", "Sales User")
		frappe.permissions.add_user_permission("Territory", "_Test Territory India", user.name)

		with self.set_user(user.name):
			rows = stage_rows(stage, from_date="2026-01-01", to_date="2026-01-31")

		self.assertEqual(rows[0]["january_2026"], 1)

	def test_assigned_to_filters_sales_stage_pipeline(self):
		stage = make_sales_stage()
		assigned = make_stage_opportunity(stage, 100, "2026-01-20")
		make_stage_opportunity(stage, 100, "2026-01-20")
		frappe.db.set_value("Opportunity", assigned.name, "_assign", '["test1@example.com"]')

		rows = stage_rows(
			stage, assigned_to="test1@example.com", from_date="2026-01-01", to_date="2026-01-31"
		)

		self.assertEqual(rows[0]["january_2026"], 1)


def make_sales_stage() -> str:
	stage = "_Test Pipeline Stage " + frappe.generate_hash(length=5)
	frappe.get_doc({"doctype": "Sales Stage", "stage_name": stage}).insert()
	return stage


def make_stage_opportunity(stage: str, amount: float, expected_closing: str, **fields):
	doc = frappe.new_doc("Opportunity")
	doc.update(
		{
			"opportunity_from": "Customer",
			"party_name": "_Test Customer",
			"company": "Best Test",
			"currency": "INR",
			"conversion_rate": 1,
			"opportunity_amount": amount,
			"transaction_date": "2025-12-01",
			"expected_closing": expected_closing,
			"sales_stage": stage,
			**fields,
		}
	)
	return doc.insert()


def stage_rows(stage: str, **filters) -> list[dict]:
	return [row for row in execute(stage_filters(**filters))[1] if row["sales_stage"] == stage]


def stage_filters(**filters) -> dict:
	return {
		"pipeline_by": "Sales Stage",
		"range": "Monthly",
		"based_on": "Number",
		"company": "Best Test",
		**filters,
	}


def create_opportunity():
	doc = frappe.db.exists({"doctype": "Opportunity", "party_name": "_Test NC"})
	if not doc:
		doc = frappe.new_doc("Opportunity")
		doc.opportunity_from = "Customer"
		customer_name = frappe.db.get_value("Customer", {"customer_name": "_Test NC"}, ["customer_name"])
		doc.party_name = customer_name
		doc.opportunity_amount = 150000
		doc.utm_source = "Cold Calling"
		doc.currency = "INR"
		doc.expected_closing = "2021-08-31"
		doc.company = "Best Test"
		doc.insert()
