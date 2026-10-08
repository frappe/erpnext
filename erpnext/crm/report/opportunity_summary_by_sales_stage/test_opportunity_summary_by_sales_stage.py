import frappe
from frappe.utils import today

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

	def test_amount_uses_opportunity_conversion_rate(self):
		opportunity_type = make_opportunity_type()
		frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": today(),
				"from_currency": "USD",
				"to_currency": "INR",
				"exchange_rate": 90,
			}
		).insert(ignore_if_duplicate=True)
		make_typed_opportunity(opportunity_type, 1000)
		make_typed_opportunity(opportunity_type, 100, currency="USD", conversion_rate=80)

		self.assertEqual(type_row(opportunity_type, data_based_on="Amount")["Prospecting"], 9000)

		# amounts of companies with different currencies can't be added together
		with self.assertRaises(frappe.ValidationError):
			type_row(opportunity_type, data_based_on="Amount", company=None)

	def test_amount_without_conversion_rate_uses_exchange_rate(self):
		opportunity_type = make_opportunity_type()
		frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": "2025-12-01",
				"from_currency": "USD",
				"to_currency": "INR",
				"exchange_rate": 85,
			}
		).insert(ignore_if_duplicate=True)
		opportunity = make_typed_opportunity(
			opportunity_type, 100, currency="USD", conversion_rate=80, transaction_date="2026-01-25"
		)
		frappe.db.set_value("Opportunity", opportunity.name, "conversion_rate", 0)

		self.assertEqual(type_row(opportunity_type, data_based_on="Amount")["Prospecting"], 8500)

	def test_opportunity_without_sales_stage(self):
		opportunity_type = make_opportunity_type()
		make_typed_opportunity(opportunity_type, 1000)
		without_stage = make_typed_opportunity(opportunity_type, 500)
		frappe.db.set_value("Opportunity", without_stage.name, "sales_stage", None)

		columns, data = execute(
			{"based_on": "Opportunity Type", "data_based_on": "Amount", "company": "Best Test"}
		)[:2]

		self.assertIn("Not Set", [column["fieldname"] for column in columns])
		self.assertEqual(type_row(opportunity_type)["Not Set"], 1)
		self.assertEqual(type_row(opportunity_type, data_based_on="Amount")["Not Set"], 500)


def make_opportunity_type() -> str:
	opportunity_type = "_Test Summary Type " + frappe.generate_hash(length=5)
	frappe.get_doc({"doctype": "Opportunity Type", "__newname": opportunity_type}).insert()
	return opportunity_type


def make_typed_opportunity(opportunity_type: str, amount: float, **fields):
	doc = frappe.new_doc("Opportunity")
	doc.update(
		{
			"opportunity_from": "Customer",
			"party_name": "_Test Customer",
			"opportunity_type": opportunity_type,
			"company": "Best Test",
			"currency": "INR",
			"conversion_rate": 1,
			"opportunity_amount": amount,
			"sales_stage": "Prospecting",
			**fields,
		}
	)
	return doc.insert()


def type_row(opportunity_type: str, **filters) -> dict:
	filters = {"based_on": "Opportunity Type", "data_based_on": "Number", "company": "Best Test", **filters}
	return next(row for row in execute(filters)[1] if row["opportunity_type"] == opportunity_type)
