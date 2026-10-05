# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.crm.report.campaign_efficiency.campaign_efficiency import execute


class TestCampaignEfficiency(FrappeTestCase):
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
		from erpnext.crm.doctype.lead.lead import make_customer

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
		campaign = make_campaign("_Test Campaign Eff Permissions")
		make_campaign_lead(campaign, territory="_Test Territory")
		hidden_lead = make_campaign_lead(campaign, territory="_Test Territory India")
		make_lead_quotation(hidden_lead.name).submit()

		user = make_sales_user("campaign_eff_territory@example.com")
		frappe.permissions.add_user_permission("Territory", "_Test Territory", user)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(user)
		row = campaign_row(campaign)

		self.assertEqual(row["lead_count"], 1)
		self.assertEqual(row["quot_count"], 0)

	def test_converted_customer_limited_to_user_permissions(self):
		from erpnext.crm.doctype.lead.lead import make_customer

		campaign = make_campaign("_Test Campaign Eff Customer Permissions")
		lead = make_campaign_lead(campaign, company_name="_Test Campaign Eff Hidden Customer")
		customer = make_customer(lead.name)
		customer.customer_group = "_Test Customer Group"
		customer.territory = "_Test Territory"
		customer.insert()
		quotation = make_lead_quotation(lead.name)
		quotation.quotation_to = "Customer"
		quotation.party_name = customer.name
		quotation.save()
		quotation.submit()

		user = make_sales_user("campaign_eff_customer@example.com")
		frappe.permissions.add_user_permission("Customer", "_Test Customer", user)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(user)
		row = campaign_row(campaign)

		self.assertEqual(row["lead_count"], 1)
		self.assertEqual(row["quot_count"], 0)

	def test_cancelled_orders_left_out(self):
		campaign = make_campaign("_Test Campaign Eff Orders")
		lead = make_campaign_lead(campaign)
		quotation = make_lead_quotation(lead.name)
		quotation.submit()

		cancelled = make_sales_order_for(quotation.name)
		cancelled.cancel()
		make_sales_order_for(quotation.name)

		row = campaign_row(campaign)
		self.assertEqual(row["order_count"], 1)
		self.assertEqual(row["order_value"], 1000)


def make_sales_user(email: str) -> str:
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		)
		user.append("roles", {"role": "Sales User"})
		user.insert(ignore_permissions=True)
	return email


def make_campaign(campaign_name: str) -> str:
	if campaign := frappe.db.get_value("Campaign", {"campaign_name": campaign_name}):
		return campaign
	return frappe.get_doc({"doctype": "Campaign", "campaign_name": campaign_name}).insert().name


def make_campaign_lead(campaign: str, **fields):
	return frappe.get_doc(
		{"doctype": "Lead", "lead_name": f"_Test Lead {campaign}", "campaign_name": campaign, **fields}
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
	from erpnext.selling.doctype.quotation.quotation import make_sales_order

	sales_order = make_sales_order(quotation)
	if item_code:
		sales_order.items = [item for item in sales_order.items if item.item_code == item_code]
	sales_order.delivery_date = add_days(nowdate(), 7)
	sales_order.insert()
	sales_order.submit()
	return sales_order


def campaign_row(campaign: str, filters: dict | None = None) -> dict:
	filters = frappe._dict(filters or {"from_date": add_days(nowdate(), -1), "to_date": nowdate()})
	return next(row for row in execute(filters)[1] if row["campaign_name"] == campaign)
