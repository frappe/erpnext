# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.crm.doctype.opportunity.test_opportunity import make_opportunity
from erpnext.crm.report.lost_opportunity.lost_opportunity import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestLostOpportunity(ERPNextTestSuite):
	def test_territory_group_includes_child_territories(self):
		opportunity = make_lost_opportunity(["_Test Lost Reason A"], territory="_Test Territory India")

		data = run_report(territory="All Territories")
		self.assertIn(opportunity.name, [row.name for row in data])

	def test_later_edit_keeps_opportunity_in_its_lost_period(self):
		opportunity = make_lost_opportunity(["_Test Lost Reason A"])
		lost_on = add_days(today(), -30)
		opportunity.db_set("lost_on", lost_on)
		opportunity.reload()
		opportunity.order_lost_reason = "Edited after it was lost"
		opportunity.save()

		lost_period = run_report(from_date=lost_on, to_date=lost_on)
		self.assertIn(opportunity.name, [row.name for row in lost_period])
		self.assertNotIn(opportunity.name, [row.name for row in run_report()])

	def test_lost_reason_filter_keeps_every_reason(self):
		opportunity = make_lost_opportunity(["_Test Lost Reason A", "_Test Lost Reason B"])

		row = next(
			row for row in run_report(lost_reason="_Test Lost Reason A") if row.name == opportunity.name
		)
		self.assertCountEqual(row.lost_reason.split(", "), ["_Test Lost Reason A", "_Test Lost Reason B"])


def make_lost_opportunity(lost_reasons: list, **fields):
	opportunity = make_opportunity()
	opportunity.update(fields)
	opportunity.save()
	opportunity.declare_enquiry_lost(
		lost_reasons_list=[{"lost_reason": make_lost_reason(reason)} for reason in lost_reasons],
		competitors=[],
	)
	return opportunity


def make_lost_reason(lost_reason: str) -> str:
	if not frappe.db.exists("Opportunity Lost Reason", lost_reason):
		frappe.get_doc({"doctype": "Opportunity Lost Reason", "lost_reason": lost_reason}).insert()
	return lost_reason


def run_report(**filters):
	defaults = {"company": "_Test Company", "from_date": add_days(today(), -1), "to_date": today()}
	return execute(frappe._dict({**defaults, **filters}))[1]
