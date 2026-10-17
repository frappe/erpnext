# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.crm.report.prospects_engaged_but_not_converted.prospects_engaged_but_not_converted import (
	execute,
)
from erpnext.tests.permission_test_utils import as_user, make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestProspectsEngagedButNotConverted(ERPNextTestSuite):
	def test_report_lists_only_records_the_user_can_read(self):
		own_lead = make_lead_with_communication("_Test Prospect Own Company", company="_Test Company")
		other_lead = make_lead_with_communication("_Test Prospect Other Company", company="_Test Company 1")
		issue = frappe.get_doc(
			{"doctype": "Issue", "subject": "_Test Prospect Issue", "lead": own_lead}
		).insert(ignore_permissions=True)
		add_received_communication("Issue", issue.name, "_Test Prospect Issue")
		same_name_issue = frappe.get_doc({"doctype": "Issue", "subject": "_Test Prospect Same Name"})
		same_name_issue.insert(set_name=own_lead, ignore_permissions=True)
		add_received_communication("Issue", same_name_issue.name, "_Test Prospect Same Name")

		filters = frappe._dict(no_of_interaction=5, lead_age=60)
		all_rows = execute(frappe._dict(filters))[1]
		expected_own_rows = [row for row in all_rows if row[0] == own_lead and row[3] == "Lead"]
		self.assertTrue(expected_own_rows)
		self.assertIn(issue.name, {row[4] for row in all_rows})

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


def make_lead_with_communication(lead_name: str, company: str) -> str:
	lead = frappe.get_doc({"doctype": "Lead", "lead_name": lead_name, "company": company}).insert()
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
