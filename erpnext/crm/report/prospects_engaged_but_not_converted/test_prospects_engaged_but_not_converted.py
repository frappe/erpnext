# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, now_datetime

from erpnext.crm.report.prospects_engaged_but_not_converted.prospects_engaged_but_not_converted import (
	execute,
)
from erpnext.tests.permission_test_utils import as_user, make_fenced_user
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

	def test_report_lists_only_records_the_user_can_read(self):
		own_lead = make_lead_with_communication(
			"_Test Prospect Own Company", days_old=90, company="_Test Company"
		)
		other_lead = make_lead_with_communication(
			"_Test Prospect Other Company", days_old=90, company="_Test Company 1"
		)
		issue = frappe.get_doc(
			{"doctype": "Issue", "subject": "_Test Prospect Issue", "lead": own_lead}
		).insert(ignore_permissions=True)
		add_received_communication("Issue", issue.name, "_Test Prospect Issue")
		same_name_issue = frappe.get_doc({"doctype": "Issue", "subject": "_Test Prospect Same Name"})
		same_name_issue.insert(set_name=own_lead, ignore_permissions=True)
		add_received_communication("Issue", same_name_issue.name, "_Test Prospect Same Name")

		filters = frappe._dict(no_of_interaction=5, lead_age=60)
		expected_own_rows = [row for row in execute(filters)[1] if row[0] == own_lead and row[3] == "Lead"]
		sales_user = make_fenced_user(
			"prospects-sales@example.com", ["Sales User"], [("Company", "_Test Company")]
		)
		with as_user(sales_user):
			rows = execute(frappe._dict(filters))[1]

		self.assertEqual([row for row in rows if row[0] == own_lead and row[3] == "Lead"], expected_own_rows)
		self.assertNotIn(other_lead, {row[0] for row in rows})
		self.assertNotIn("Issue", {row[3] for row in rows})
		self.assertNotIn("_Test Prospect Same Name", {row[5] for row in rows})

		with as_user(make_fenced_user("prospects-website@example.com", [])):
			self.assertRaises(frappe.PermissionError, execute, frappe._dict(filters))


def make_lead_with_communication(lead_name: str, days_old: int, company: str | None = None) -> str:
	lead = frappe.get_doc({"doctype": "Lead", "lead_name": lead_name, "company": company}).insert()
	backdate_creation(lead.name, days=days_old)
	add_received_communication("Lead", lead.name, lead_name)
	return lead.name


def add_received_communication(reference_doctype: str, reference_name: str, content: str):
	frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"subject": content,
			"content": content,
			"sent_or_received": "Received",
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		}
	).insert()


def backdate_creation(lead: str, days: int):
	frappe.db.set_value("Lead", lead, "creation", add_days(now_datetime(), -days), update_modified=False)
