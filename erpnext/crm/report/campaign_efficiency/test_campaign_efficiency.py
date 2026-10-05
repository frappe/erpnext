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

	def test_partly_ordered_quotation_counts_as_ordered(self):
		campaign = make_campaign("_Test Campaign Eff Partly Ordered")
		lead = make_campaign_lead(campaign)
		quotation = make_lead_quotation(lead.name, item_codes=["_Test Item", "_Test Item 2"])
		quotation.submit()
		sales_order = make_sales_order_for(quotation.name, item_code="_Test Item")

		row = campaign_row(campaign)
		self.assertEqual(frappe.db.get_value("Quotation", quotation.name, "status"), "Partially Ordered")
		self.assertEqual(row["order_count"], 1)
		self.assertEqual(row["order_value"], sales_order.base_net_total)

	def test_activity_after_conversion_is_counted(self):
		from erpnext.crm.doctype.lead.mapper import make_customer

		campaign = make_campaign("_Test Campaign Eff Converted")
		lead = make_campaign_lead(campaign, company_name="_Test Campaign Eff Converted Customer")
		customer = make_customer(lead.name)
		customer.customer_group = "_Test Customer Group"
		customer.territory = "_Test Territory"
		customer.insert()

		quotation = make_lead_quotation(lead.name)
		quotation.quotation_to = "Customer"
		quotation.party_name = customer.name
		quotation.save()
		quotation.submit()
		make_sales_order_for(quotation.name)

		row = campaign_row(campaign)
		self.assertEqual(row["quot_count"], 1)
		self.assertEqual(row["order_count"], 1)
		self.assertEqual(row["order_value"], 1000)

	def test_leads_limited_to_user_permissions(self):
		from erpnext.buying.test_utils import create_user_with_roles

		campaign = make_campaign("_Test Campaign Eff Permissions")
		make_campaign_lead(campaign, territory="_Test Territory")
		hidden_lead = make_campaign_lead(campaign, territory="_Test Territory India")
		make_lead_quotation(hidden_lead.name).submit()

		user = create_user_with_roles("campaign_eff_territory@example.com", "Sales User")
		frappe.permissions.add_user_permission("Territory", "_Test Territory", user.name)
		with self.set_user(user.name):
			row = campaign_row(campaign)

		self.assertEqual(row["lead_count"], 1)
		self.assertEqual(row["quot_count"], 0)


def make_campaign(campaign: str) -> str:
	if not frappe.db.exists("UTM Campaign", campaign):
		frappe.get_doc({"doctype": "UTM Campaign", "__newname": campaign}).insert()
	return campaign


def make_campaign_lead(campaign: str, **fields):
	return frappe.get_doc(
		{"doctype": "Lead", "lead_name": f"_Test Lead {campaign}", "utm_campaign": campaign, **fields}
	).insert()


def make_lead_quotation(lead: str, item_codes: list | None = None):
	return frappe.get_doc(
		{
			"doctype": "Quotation",
			"quotation_to": "Lead",
			"party_name": lead,
			"company": "_Test Company",
			"items": [{"item_code": code, "qty": 1, "rate": 1000} for code in item_codes or ["_Test Item"]],
		}
	).insert()


def make_sales_order_for(quotation: str, item_code: str | None = None):
	from erpnext.selling.doctype.quotation.mapper import make_sales_order

	sales_order = make_sales_order(quotation)
	if item_code:
		sales_order.items = [item for item in sales_order.items if item.item_code == item_code]
	sales_order.delivery_date = add_days(nowdate(), 7)
	sales_order.insert()
	sales_order.submit()
	return sales_order


def campaign_row(campaign: str, filters: dict | None = None) -> dict:
	filters = frappe._dict(filters or {"from_date": add_days(nowdate(), -1), "to_date": nowdate()})
	return next(row for row in execute(filters)[1] if row["utm_campaign"] == campaign)
