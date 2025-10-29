from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.report.wbs_summary_report import wbs_summary_report


class TestWbsSummaryReport(FrappeTestCase):
	def test_execute_with_empty_filters_TC_ACC_589(self):
		"""Test execute() with no filters (just checks structure)"""

		fake_data = [
			{
				"name": "WBS-001",
				"wbs_name": "Planning",
				"amt_allocated": 100,
				"amt_utilized": 50,
				"amt_balanced": 50,
				"total_utilized": 50,
			}
		]

		with patch.object(wbs_summary_report, "get_data", return_value=fake_data):
			columns, data = wbs_summary_report.execute(filters={})

		# assert columns is not empty
		self.assertEqual(data[0]["name"], "WBS-001")

	def test_execute_with_filters_TC_ACC_590(self):
		"""Test execute() with filters covering branch where filters exist"""

		fake_data = [
			{
				"name": "WBS-002",
				"wbs_name": "Execution",
				"amt_allocated": 200,
				"amt_utilized": 100,
				"amt_balanced": 100,
				"total_utilized": 50,
			}
		]

		with patch.object(wbs_summary_report, "get_data", return_value=fake_data) as mock_get:
			columns, data = wbs_summary_report.execute(filters={"project": "Test Project"})
			mock_get.assert_called_once_with({"project": "Test Project"})

		self.assertEqual(data[0]["name"], "WBS-002")

	def test_get_data_direct_TC_ACC_591(self):
		# Create a unique suffix to avoid duplicate names across tests
		unique_suffix = frappe.generate_hash(length=5)

		#  Create temporary Company
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": f"Test Company {unique_suffix}",
				"abbr": f"TC{unique_suffix}",
				"default_currency": "INR",
			}
		).insert(ignore_permissions=True)

		#  Create temporary Project (use custom name to bypass auto series)
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"name": f"Test-Project-{unique_suffix}",
				"project_name": f"Test Project {unique_suffix}",
				"company": company.name,
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

		#  Create Work Breakdown Structure linked to the above
		frappe.get_doc(
			{
				"doctype": "Work Breakdown Structure",
				"company": company.name,
				"project": project.name,
				"wbs_name": "Planning",
				"overall_budget": 100,
				"assigned_overall_budget": 40,
				"is_group": 0,
				"wbs_level": "Level 1",
			}
		).insert(ignore_permissions=True)

		#  Call your function
		filters = {"company": company.name, "project": project.name, "wbs_name": "Planning"}
		result = wbs_summary_report.get_data(filters)

		#  Assertions
		self.assertIsInstance(result, list)
		self.assertEqual(result[0]["wbs_name"], "Planning")

	def test_get_columns_and_add_to_tree_TC_ACC_592(self):
		"""Test get_columns() and add_to_tree() logic"""

		# 1. Test get_columns()
		columns = wbs_summary_report.get_columns()
		self.assertIsInstance(columns, list)
		self.assertGreater(len(columns), 0)
		self.assertIn("fieldname", columns[0])
		self.assertEqual(columns[0]["fieldname"], "name")

		# 2. Test add_to_tree()
		parent_id = "WBS-001"
		wbs_map = {
			parent_id: [
				{
					"name": "WBS-Child-1",
					"project_name": "Test Project",
					"wbs_name": "Child Planning",
					"wbs_level": "Level 2",
					"amt_allocated": 50,
					"amt_utilized": 20,
					"amt_balanced": 30,
					"total_utilized": 40,
				}
			]
		}

		tree_data = []
		totals = {"amt_allocated": 0, "amt_utilized": 0, "amt_balanced": 0, "total_utilized_percent": 0}

		# Call add_to_tree with fake data
		wbs_summary_report.add_to_tree(parent_id, 1, wbs_map, tree_data, totals)

		# Assertions
		self.assertEqual(tree_data[0]["name"], "WBS-Child-1")

		# Totals should be updated
		self.assertEqual(totals["amt_allocated"], 50)
		self.assertEqual(totals["amt_utilized"], 20)
