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
