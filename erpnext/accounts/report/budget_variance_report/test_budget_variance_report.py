# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.accounts.report.budget_variance_report.budget_variance_report import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestBudgetVarianceReport(ERPNextTestSuite):
	def test_report_executes(self):
		# Smoke-guards the raw-SQL -> query-builder port: the report query must compile and run on
		# both MariaDB and postgres.
		company = frappe.db.get_value("Company", {}, "name")
		fy = frappe.db.get_value("Fiscal Year", {}, "name", order_by="year_start_date desc")
		columns, *_rest = execute(
			frappe._dict(
				{
					"company": company,
					"from_fiscal_year": fy,
					"to_fiscal_year": fy,
					"period": "Yearly",
					"budget_against": "Cost Center",
				}
			)
		)
		self.assertTrue(columns)
