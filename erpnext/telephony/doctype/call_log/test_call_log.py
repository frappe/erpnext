# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import random
import string
from unittest.mock import patch

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.telephony.doctype.call_log.call_log import (
	add_call_summary_and_call_type,
	get_linked_call_logs,
	link_existing_conversations,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestCallLog(ERPNextTestSuite):
	def setUp(self):
		# A fresh, unused 8-digit suffix guarantees the controller's before_insert
		# auto-linking (Contact/Lead lookup) finds nothing, so the only Dynamic Link
		# rows present are the ones this test creates.
		self.number = "98" + "".join(random.choices(string.digits, k=8))

		# Two Call Logs that share the same phone number: one via `to`, one via
		# `from`. Both must be matched by the `from LIKE | to LIKE` predicate, and
		# the leading "+91" / "0" prefixes exercise strip_number normalisation
		# (the trailing digits still end with self.number).
		self.linked_log = self._make_call_log(to=f"+91{self.number}", type="Incoming")
		self.unlinked_log = self._make_call_log(**{"from": f"0{self.number}", "type": "Outgoing"})

		# The target doc the existing conversations get linked to. A real Contact
		# (with a name + matching phone) is required so link_existing_conversations
		# accepts it (doctype == "Contact") and reads doc.phone_nos / doc.name.
		self.contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": f"_Test Caller {self.number}",
				"phone_nos": [{"phone": self.number, "is_primary_phone": 1}],
			}
		)
		# Suppress the Contact's own after_insert auto-link hook during insert, so
		# the test controls exactly which log is pre-linked (the hook is invoked
		# explicitly via _run_linker once the fixtures are in place).
		self.contact.flags.ignore_auto_link_call_log = True
		self.contact.insert(ignore_permissions=True)

		# Pre-link ONLY one of the two logs to the contact via a Dynamic Link row.
		# The converted HAVING SUM(CASE ...) == 0 filter must therefore exclude
		# this log and return the other when link_existing_conversations runs.
		self._add_link(self.linked_log, "Contact", self.contact.name)

	def _make_call_log(self, **kwargs):
		doc = frappe.get_doc({"doctype": "Call Log", "id": frappe.generate_hash(length=10), **kwargs})
		doc.insert(ignore_permissions=True)
		return doc.name

	def _add_link(self, call_log, link_doctype, link_name):
		doc = frappe.get_doc("Call Log", call_log)
		doc.append("links", {"link_doctype": link_doctype, "link_name": link_name})
		doc.save(ignore_permissions=True)

	def _run_linker(self):
		# Clear the flag set during insert so the explicit call actually runs the
		# converted LEFT JOIN / GROUP BY / HAVING query path.
		self.contact.flags.ignore_auto_link_call_log = False
		link_existing_conversations(self.contact, "Open")

	def _contact_links_of(self, call_log):
		return frappe.get_all(
			"Dynamic Link",
			filters={"parenttype": "Call Log", "parent": call_log, "link_doctype": "Contact"},
			fields=["link_name"],
			pluck="link_name",
		)

	def test_links_previously_unlinked_log(self):
		"""The converted query's HAVING == 0 returns the log NOT yet linked to the
		contact, so link_existing_conversations adds the Contact link to it."""
		self.assertEqual(self._contact_links_of(self.unlinked_log), [], "precondition")

		self._run_linker()

		self.assertEqual(
			self._contact_links_of(self.unlinked_log),
			[self.contact.name],
			"Previously-unlinked log matching the number must gain the Contact link",
		)

	def test_linking_does_not_commit(self):
		with patch.object(frappe, "in_test", False), patch.object(frappe.db, "commit") as commit:
			self._run_linker()

		commit.assert_not_called()
		self.assertEqual(self._contact_links_of(self.unlinked_log), [self.contact.name])

	def test_already_linked_log_is_not_relinked(self):
		"""The HAVING SUM(CASE ...) == 0 must EXCLUDE the already-linked log from the returned set,
		so link_existing_conversations never re-saves it. Asserting only the link count is not enough
		(validate() -> deduplicate_dynamic_links strips a duplicate either way), so pin the HAVING by
		asserting the already-linked log was never touched: an excluded log is not in `logs`, so
		add_link()/save() never runs and its `modified` timestamp is unchanged."""
		self.assertEqual(self._contact_links_of(self.linked_log), [self.contact.name], "precondition")
		modified_before = frappe.db.get_value("Call Log", self.linked_log, "modified")

		self._run_linker()

		# Excluded by HAVING -> never re-saved -> modified unchanged. (If HAVING were dropped/inverted
		# the log would be returned, re-saved, and modified would bump.)
		self.assertEqual(
			frappe.db.get_value("Call Log", self.linked_log, "modified"),
			modified_before,
			"Already-linked log must be excluded by HAVING and never re-saved",
		)
		self.assertEqual(self._contact_links_of(self.linked_log), [self.contact.name])

	def test_log_not_matching_number_is_untouched(self):
		"""A log whose from/to does not contain the number is excluded by the
		from/to LIKE predicate and must stay unlinked."""
		other = self._make_call_log(**{"from": "+919999999999", "to": "+918888888888", "type": "Outgoing"})

		self._run_linker()

		self.assertEqual(self._contact_links_of(other), [], "Log not matching the number must stay unlinked")

	def test_agent_can_save_summary_of_own_call(self):
		user = "test_call_agent@example.com"
		employee = make_employee(user, company="_Test Company")
		call_type = frappe.get_doc({"doctype": "Telephony Call Type", "call_type": "_Test Call Type"})
		call_type.insert(ignore_if_duplicate=True)
		call_log = self._make_call_log(
			**{"from": "+919999999999", "type": "Outgoing"},
			call_received_by=employee,
			employee_user_id=user,
		)

		frappe.set_user(user)
		try:
			add_call_summary_and_call_type(call_log, "Wants a quote", "_Test Call Type")
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(frappe.db.get_value("Call Log", call_log, "type_of_call"), "_Test Call Type")

	def test_timeline_shows_only_permitted_call_logs(self):
		self.assertEqual(len(get_linked_call_logs("Contact", self.contact.name)), 1)

		user = "test_call_log_sales_user@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Sales",
					"send_welcome_email": 0,
					"roles": [{"role": "Sales User"}],
				}
			).insert(ignore_permissions=True)

		frappe.set_user(user)
		try:
			self.assertEqual(get_linked_call_logs("Contact", self.contact.name), [])
		finally:
			frappe.set_user("Administrator")

	def test_transferred_call_is_stored_with_the_new_agent(self):
		first_agent = make_employee(
			"test_call_agent_a@example.com", company="_Test Company", cell_number=f"+91{self.number}1"
		)
		second_agent = make_employee(
			"test_call_agent_b@example.com", company="_Test Company", cell_number=f"+91{self.number}2"
		)
		call_log = frappe.get_doc(
			"Call Log", self._make_call_log(to=f"+91{self.number}1", type="Incoming", status="Ringing")
		)
		self.assertEqual(call_log.call_received_by, first_agent)

		call_log.to = f"+91{self.number}2"
		call_log.save(ignore_permissions=True)

		self.assertEqual(
			frappe.db.get_value("Call Log", call_log.name, ["call_received_by", "employee_user_id"]),
			(second_agent, "test_call_agent_b@example.com"),
		)
