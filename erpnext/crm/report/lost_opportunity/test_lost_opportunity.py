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

	def test_territory_group_includes_child_territories(self):
		opportunity = make_lost_opportunity(["_Test Lost Reason A"], territory="_Test Territory India")

		data = run_report(territory="All Territories")
		self.assertIn(opportunity.name, [row.name for row in data])

	def test_lost_reason_filter_keeps_every_reason(self):
		opportunity = make_lost_opportunity(["_Test Lost Reason A", "_Test Lost Reason B"])

		row = next(
			row for row in run_report(lost_reason="_Test Lost Reason A") if row.name == opportunity.name
		)
		self.assertCountEqual(row.lost_reason.split(", "), ["_Test Lost Reason A", "_Test Lost Reason B"])


def make_lost_opportunity(lost_reasons: list, **fields):
	from erpnext.crm.doctype.opportunity.test_opportunity import _ensure_master, make_opportunity

	opportunity = make_opportunity()
	opportunity.update(fields)
	opportunity.save()
	opportunity.declare_enquiry_lost(
		lost_reasons_list=[
			{"lost_reason": _ensure_master("Opportunity Lost Reason", "lost_reason", reason)}
			for reason in lost_reasons
		],
		competitors=[],
	)
	return opportunity


def run_report(**filters):
	return execute(
		frappe._dict(company="_Test Company", from_date=add_days(today(), -1), to_date=today(), **filters)
	)[1]
