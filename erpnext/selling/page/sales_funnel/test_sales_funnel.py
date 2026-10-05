# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, random_string, today

from erpnext.crm.doctype.opportunity.test_opportunity import make_opportunity
from erpnext.selling.doctype.quotation.test_quotation import make_quotation
from erpnext.selling.page.sales_funnel.sales_funnel import get_funnel_data
from erpnext.tests.utils import ERPNextTestSuite


class TestSalesFunnel(ERPNextTestSuite):
	def get_stage_value(self, data, title):
		for stage in data:
			if stage["title"] == title:
				return stage["value"]
		self.fail(f"Stage {title!r} not found in funnel data: {data}")

	def make_lead(self, company):
		# The funnel filters Lead on `company`, which the shared crm make_lead()
		# helper does not set, so build the Lead directly here.
		return frappe.get_doc(
			{
				"doctype": "Lead",
				"first_name": "_Test Funnel",
				"last_name": random_string(6),
				"email_id": f"funnel_{random_string(8)}@example.com",
				"company": company,
				"status": "Lead",
			}
		).insert(ignore_permissions=True)

	def test_funnel_lead_and_opportunity_counts(self):
		company = "_Test Company"
		# validate_filters() rejects from_date >= to_date, and the query matches on
		# Date(creation), so use [today, tomorrow] to capture docs created today.
		from_date, to_date = today(), add_days(today(), 1)

		# Baseline before creating anything (robust against pre-existing rows).
		baseline = get_funnel_data(from_date, to_date, company)
		baseline_leads = self.get_stage_value(baseline, "Active Leads")
		baseline_opportunities = self.get_stage_value(baseline, "Opportunities")

		# Create two leads for this company today.
		lead_1 = self.make_lead(company)
		self.make_lead(company)

		# Create one opportunity (opportunity_from='Lead') against one of the leads.
		opportunity = make_opportunity(
			company=company,
			opportunity_from="Lead",
			lead=lead_1.name,
		)
		self.assertEqual(opportunity.opportunity_from, "Lead")
		self.assertEqual(opportunity.party_name, lead_1.name)

		after = get_funnel_data(from_date, to_date, company)
		after_leads = self.get_stage_value(after, "Active Leads")
		after_opportunities = self.get_stage_value(after, "Opportunities")

		# The two new leads and one new opportunity must be reflected exactly.
		self.assertEqual(after_leads - baseline_leads, 2)
		self.assertEqual(after_opportunities - baseline_opportunities, 1)

		# Sanity: counts are at least what we created.
		self.assertGreaterEqual(after_leads, 2)
		self.assertGreaterEqual(after_opportunities, 1)

	def test_funnel_filters_by_company(self):
		# A lead for a different company must not inflate the target company's count.
		company = "_Test Company"
		other_company = "_Test Company 1"
		from_date, to_date = today(), add_days(today(), 1)

		baseline_leads = self.get_stage_value(get_funnel_data(from_date, to_date, company), "Active Leads")

		# Lead created for a different company.
		self.make_lead(other_company)

		after_leads = self.get_stage_value(get_funnel_data(from_date, to_date, company), "Active Leads")
		self.assertEqual(after_leads, baseline_leads)

	def test_funnel_quotations_count(self):
		company = "_Test Company"
		from_date, to_date = today(), add_days(today(), 1)

		baseline_quotations = self.get_stage_value(get_funnel_data(from_date, to_date, company), "Quotations")

		lead = self.make_lead(company)
		lead_opportunity = make_opportunity(company=company, opportunity_from="Lead", lead=lead.name)
		lead_quotation = make_quotation(party_name="_Test Customer", company=company, do_not_submit=True)
		lead_quotation.opportunity = lead_opportunity.name
		lead_quotation.submit()

		customer_opportunity = make_opportunity(company=company, opportunity_from="Customer")
		customer_quotation = make_quotation(party_name="_Test Customer", company=company, do_not_submit=True)
		customer_quotation.opportunity = customer_opportunity.name
		customer_quotation.submit()

		after_quotations = self.get_stage_value(get_funnel_data(from_date, to_date, company), "Quotations")
		self.assertEqual(after_quotations - baseline_quotations, 1)

	def test_funnel_converted_count(self):
		# A Customer joined to a Lead of this company (Customer INNER JOIN Lead on
		# lead_name) must be reflected in the Converted stage.
		company = "_Test Company"
		from_date, to_date = today(), add_days(today(), 1)

		baseline_converted = self.get_stage_value(get_funnel_data(from_date, to_date, company), "Converted")

		lead = self.make_lead(company)
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": f"_Test Funnel Customer {random_string(6)}",
				"customer_type": "Company",
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
				"lead_name": lead.name,
			}
		).insert(ignore_permissions=True)

		after_converted = self.get_stage_value(get_funnel_data(from_date, to_date, company), "Converted")
		self.assertEqual(after_converted - baseline_converted, 1)
		self.assertGreaterEqual(after_converted, 1)

	def roles_that_read(self, *doctypes):
		roles = set()
		for doctype in doctypes:
			perms = frappe.get_all(
				"Custom DocPerm", filters={"parent": doctype, "read": 1, "permlevel": 0}, pluck="role"
			) or frappe.get_all(
				"DocPerm", filters={"parent": doctype, "read": 1, "permlevel": 0}, pluck="role"
			)
			roles.update(perms)
		return roles

	def test_funnel_counts_respect_user_permissions(self):
		company = "_Test Company"
		from_date, to_date = today(), add_days(today(), 1)
		territories = frappe.get_all("Territory", filters={"is_group": 0}, pluck="name", limit=2)

		lead = self.make_lead(company)
		lead.db_set("territory", territories[1])

		roles = self.roles_that_read("Lead", "Opportunity", "Quotation", "Customer", "Company")
		email = f"funnel-perm-{random_string(6)}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Funnel Perm",
				"send_welcome_email": 0,
				"roles": [{"role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": email,
				"allow": "Territory",
				"for_value": territories[0],
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)

		admin_leads = self.get_stage_value(get_funnel_data(from_date, to_date, company), "Active Leads")
		frappe.set_user(email)
		try:
			self.assertEqual(frappe.get_list("Lead", filters={"name": lead.name}, pluck="name"), [])
			restricted_leads = self.get_stage_value(
				get_funnel_data(from_date, to_date, company), "Active Leads"
			)
		finally:
			frappe.set_user("Administrator")

		self.assertGreater(admin_leads, restricted_leads)
