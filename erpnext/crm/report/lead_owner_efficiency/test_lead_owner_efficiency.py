# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.crm.report.lead_owner_efficiency.lead_owner_efficiency import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestLeadOwnerEfficiency(ERPNextTestSuite):
	"""Groups leads by their owner and counts the opportunity/quotation/order funnel
	derived from those leads."""

	def setUp(self):
		# a unique owner keeps the per-owner counts isolated from other tests' leads
		self.owner = self.make_user()

	def make_user(self):
		email = f"lead_owner_{frappe.generate_hash(length=8)}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Lead Owner", "send_welcome_email": 0}
		).insert()
		return email

	def make_lead(self):
		return frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": f"Lead {frappe.generate_hash(length=6)}",
				"lead_owner": self.owner,
				"company": "_Test Company",
			}
		).insert()

	def run_report(self, **extra):
		filters = frappe._dict({"from_date": add_days(today(), -1), "to_date": today()})
		filters.update(extra)
		return execute(filters)[1]

	def owner_row(self, data):
		return next((r for r in data if r["lead_owner"] == self.owner), None)

	def test_lead_count_grouped_by_owner(self):
		self.make_lead()
		self.make_lead()

		row = self.owner_row(self.run_report())
		self.assertIsNotNone(row, "Lead owner missing from report")
		self.assertEqual(row["lead_count"], 2)
		self.assertEqual(row["opp_count"], 0)
		self.assertEqual(row["opp_lead"], 0.0)

	def test_opportunity_from_lead_is_counted(self):
		lead = self.make_lead()
		frappe.get_doc(
			{
				"doctype": "Opportunity",
				"opportunity_from": "Lead",
				"party_name": lead.name,
				"company": "_Test Company",
				"currency": "INR",
			}
		).insert()

		row = self.owner_row(self.run_report())
		self.assertIsNotNone(row, "Lead owner missing from report")
		self.assertEqual(row["lead_count"], 1)
		self.assertEqual(row["opp_count"], 1)
		# one opportunity from one lead -> 100% opp/lead conversion
		self.assertEqual(row["opp_lead"], 100.0)
