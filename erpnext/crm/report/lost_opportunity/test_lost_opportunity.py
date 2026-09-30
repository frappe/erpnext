# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.crm.report.lost_opportunity.lost_opportunity import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestLostOpportunity(ERPNextTestSuite):
	def test_report_aggregates_lost_reasons(self):
		# Exercises the db-aware GROUP_CONCAT (MariaDB) / STRING_AGG (postgres) aggregation of the
		# child "Opportunity Lost Reason Detail" rows. The MySQL-only GROUP_CONCAT term would fail to
		# compile on postgres, so simply running the report query guards the portability fix on both
		# databases.
		company = frappe.db.get_value("Company", {}, "name")
		columns, data = execute(
			frappe._dict({"company": company, "from_date": add_days(today(), -365), "to_date": today()})
		)
		self.assertTrue(columns)
		self.assertIsInstance(data, list)
