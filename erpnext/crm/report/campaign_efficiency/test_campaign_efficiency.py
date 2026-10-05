# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.crm.report.campaign_efficiency.campaign_efficiency import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestCampaignEfficiency(ERPNextTestSuite):
	def test_lead_count_per_campaign(self):
		"""execute() groups Leads by utm_campaign over a creation-date window and counts leads per
		group. Seed two Leads sharing one distinct UTM Campaign, run the report over a window that
		includes their (now-dated) creation, and assert that campaign's row reports lead_count == 2.
		The group is unique to this test, so the count is exact rather than a tautology, and both
		MariaDB and Postgres must return the same row/value."""
		campaign = "_Test Campaign Eff Campaign"
		if not frappe.db.exists("UTM Campaign", campaign):
			frappe.get_doc({"doctype": "UTM Campaign", "__newname": campaign}).insert(ignore_permissions=True)

		for i in range(2):
			frappe.get_doc(
				{
					"doctype": "Lead",
					"lead_name": f"_Test Campaign Eff Lead {i}",
					"utm_campaign": campaign,
				}
			).insert(ignore_permissions=True)

		# from_date <= creation(now) < to_date + 1 -> window covers the freshly inserted leads
		filters = frappe._dict(
			{
				"from_date": add_days(nowdate(), -7),
				"to_date": add_days(nowdate(), 1),
				"based_on": "utm_campaign",
			}
		)
		columns, data = execute(filters)

		row = next((r for r in data if r.get("utm_campaign") == campaign), None)
		self.assertIsNotNone(row, "campaign row missing from report output")
		self.assertEqual(row["lead_count"], 2)
		# no quotations/orders seeded for these leads -> derived counts are zero
		self.assertEqual(row["quot_count"], 0)
		self.assertEqual(row["order_count"], 0)

	def test_cancelled_and_draft_documents_left_out(self):
		campaign = "_Test Campaign Eff Orders"
		if not frappe.db.exists("UTM Campaign", campaign):
			frappe.get_doc({"doctype": "UTM Campaign", "__newname": campaign}).insert()
		lead = frappe.get_doc(
			{"doctype": "Lead", "lead_name": "_Test Campaign Eff Order Lead", "utm_campaign": campaign}
		).insert()
		quotation = make_lead_quotation(lead.name)
		quotation.submit()

		cancelled = make_lead_sales_order(quotation.name)
		cancelled.cancel()
		make_lead_sales_order(quotation.name)
		make_lead_quotation(lead.name)
		cancelled_quotation = make_lead_quotation(lead.name)
		cancelled_quotation.submit()
		cancelled_quotation.cancel()

		row = campaign_row(campaign)
		self.assertEqual(row["quot_count"], 1)
		self.assertEqual(row["order_count"], 1)
		self.assertEqual(row["order_value"], 1000)


def make_lead_sales_order(quotation: str):
	from erpnext.selling.doctype.quotation.mapper import make_sales_order

	sales_order = make_sales_order(quotation)
	sales_order.delivery_date = add_days(nowdate(), 7)
	sales_order.insert()
	sales_order.submit()
	return sales_order


def make_lead_quotation(lead: str):
	return frappe.get_doc(
		{
			"doctype": "Quotation",
			"quotation_to": "Lead",
			"party_name": lead,
			"company": "_Test Company",
			"items": [{"item_code": "_Test Item", "qty": 1, "rate": 1000}],
		}
	).insert()


def campaign_row(campaign: str) -> dict:
	data = execute(frappe._dict({"from_date": add_days(nowdate(), -1), "to_date": nowdate()}))[1]
	return next(row for row in data if row["utm_campaign"] == campaign)
