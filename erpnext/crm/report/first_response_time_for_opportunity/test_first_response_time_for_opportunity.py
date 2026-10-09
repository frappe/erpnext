# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, getdate, nowdate

from erpnext.crm.report.first_response_time_for_opportunity.first_response_time_for_opportunity import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestFirstResponseTimeForOpportunity(ERPNextTestSuite):
	def test_avg_first_response_time_row(self):
		"""The report groups Opportunity by Date(creation) and averages first_response_time where it
		is > 0, between from_date and to_date. With a single seeded Opportunity created today and a
		known first_response_time, the report must return a row for today whose averaged value equals
		the seeded duration on both engines (Date(creation) and Avg via the query builder)."""
		response_time = 3600  # seconds (Duration)
		lead_email = "_test_frt_opp@example.com"
		lead_name = "_Test FRT Opportunity Lead"

		lead = frappe.db.exists("Lead", {"email_id": lead_email})
		if not lead:
			lead = (
				frappe.get_doc({"doctype": "Lead", "lead_name": lead_name, "email_id": lead_email})
				.insert(ignore_permissions=True)
				.name
			)

		opportunity = frappe.get_doc(
			{
				"doctype": "Opportunity",
				"opportunity_from": "Lead",
				"party_name": lead,
				"company": "_Test Company",
				"currency": "INR",
				"conversion_rate": 1,
			}
		).insert(ignore_permissions=True)

		# first_response_time is a read-only computed field; set it directly.
		frappe.db.set_value(
			"Opportunity",
			opportunity.name,
			"first_response_time",
			response_time,
			update_modified=False,
		)

		columns, data = execute(
			frappe._dict(from_date=add_days(nowdate(), -1), to_date=add_days(nowdate(), 1))
		)

		# rows are positional lists: [creation_date, avg_response_time]
		today = getdate(nowdate())
		row = next((r for r in data if getdate(r[0]) == today), None)
		self.assertIsNotNone(row, "no report row for today's grouped creation date")
		self.assertEqual(getdate(row[0]), today)
		self.assertEqual(row[1], response_time)

	def test_average_limited_to_company_and_permitted_opportunities(self):
		from erpnext.buying.test_utils import create_user_with_roles

		make_answered_opportunity(3600, territory="_Test Territory")
		make_answered_opportunity(10800, territory="_Test Territory India")
		make_answered_opportunity(7200, company="_Test Company 1", territory="_Test Territory")

		user = create_user_with_roles("frt_territory_user@example.com", "Sales User")
		frappe.permissions.add_user_permission("Territory", "_Test Territory", user.name)
		filters = frappe._dict(company="_Test Company", from_date=nowdate(), to_date=nowdate())
		with self.set_user(user.name):
			data = execute(filters)[1]

		self.assertEqual([row[1] for row in data], [3600])


def make_answered_opportunity(response_time: int, company: str = "_Test Company", **fields):
	opportunity = frappe.get_doc(
		{
			"doctype": "Opportunity",
			"opportunity_from": "Customer",
			"party_name": "_Test Customer",
			"company": company,
			**fields,
		}
	).insert()
	frappe.db.set_value("Opportunity", opportunity.name, "first_response_time", response_time)
	return opportunity
