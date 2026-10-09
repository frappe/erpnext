# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, now_datetime

from erpnext.crm.report.prospects_engaged_but_not_converted.prospects_engaged_but_not_converted import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestProspectsEngagedButNotConverted(ERPNextTestSuite):
	def test_lead_with_received_communications_appears(self):
		"""The report lists non-converted Leads that have Communications referencing them
		(reference_doctype="Lead", reference_name=lead.name) with sent_or_received="Received".
		Seed one Lead and two such Received Communications, then assert the Lead surfaces in the
		report data and that the emitted row carries the Lead -> reference_doctype/reference_name
		linkage the get_data() join relies on. Asserting a concrete row (not a count) keeps this a
		real-state smoke test that exercises the same path on both MariaDB and Postgres."""
		lead_name = "_Test Prospect Engaged"
		email = "_test_prospect_engaged@example.com"

		lead = frappe.db.exists("Lead", {"lead_name": lead_name})
		if lead:
			lead = frappe.get_doc("Lead", lead)
		else:
			lead = frappe.get_doc(
				{
					"doctype": "Lead",
					"lead_name": lead_name,
					"email_id": email,
					"company_name": "_Test Prospect Org",
				}
			).insert(ignore_permissions=True)

		# A non-converted Lead older than the default Minimum Lead Age passes the report's lead filters.
		self.assertNotEqual(lead.status, "Converted")
		backdate_creation(lead.name, days=90)

		for subject in ("_test prospect engaged 1", "_test prospect engaged 2"):
			if not frappe.db.exists(
				"Communication",
				{
					"reference_doctype": "Lead",
					"reference_name": lead.name,
					"subject": subject,
				},
			):
				frappe.get_doc(
					{
						"doctype": "Communication",
						"communication_type": "Communication",
						"subject": subject,
						"content": subject,
						"sent_or_received": "Received",
						"reference_doctype": "Lead",
						"reference_name": lead.name,
					}
				).insert(ignore_permissions=True)

		# filters are accessed via .get(...) in the report, so a plain _dict suffices
		columns, data = execute(frappe._dict(no_of_interaction=1))

		# rows are lists: [lead, lead_name, company_name, reference_doctype, reference_name, content, date]
		row = next((r for r in data if r[0] == lead.name), None)
		self.assertIsNotNone(row, "seeded Lead with Received communications missing from report data")
		self.assertEqual(row[3], "Lead")
		self.assertEqual(row[4], lead.name)
		# content comes from one of the two seeded Received communications
		self.assertIn(row[5], ("_test prospect engaged 1", "_test prospect engaged 2"))

		# no_of_interaction=1 caps the per-lead communications to 1 -> exactly one row for this Lead
		lead_rows = [r for r in data if r[0] == lead.name]
		self.assertEqual(len(lead_rows), 1)

	def test_minimum_lead_age_keeps_older_leads(self):
		old_lead = make_lead_with_communication("_Test Prospect Engaged Old", days_old=90)
		new_lead = make_lead_with_communication("_Test Prospect Engaged New", days_old=10)

		leads = {row[0] for row in execute(frappe._dict(lead_age=60))[1]}
		self.assertIn(old_lead, leads)
		self.assertNotIn(new_lead, leads)


def make_lead_with_communication(lead_name: str, days_old: int) -> str:
	lead = frappe.get_doc({"doctype": "Lead", "lead_name": lead_name}).insert()
	backdate_creation(lead.name, days=days_old)
	frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"subject": lead_name,
			"content": lead_name,
			"sent_or_received": "Received",
			"reference_doctype": "Lead",
			"reference_name": lead.name,
		}
	).insert()
	return lead.name


def backdate_creation(lead: str, days: int):
	frappe.db.set_value("Lead", lead, "creation", add_days(now_datetime(), -days), update_modified=False)
