# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import random
import string
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.telephony.doctype.call_log.call_log import (
	add_call_summary_and_call_type,
	get_linked_call_logs,
	link_existing_conversations,
)


class TestCallLog(FrappeTestCase):
	def setUp(self):
		self.number = "98" + "".join(random.choices(string.digits, k=8))

	def tearDown(self):
		frappe.db.rollback()

	def _make_call_log(self, **kwargs):
		doc = frappe.get_doc({"doctype": "Call Log", "id": frappe.generate_hash(length=10), **kwargs})
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_call_status_events_go_only_to_agents_of_the_call(self):
		agent = "test_call_agent_a@example.com"
		make_employee(agent, company="_Test Company", cell_number=f"+91{self.number}1")
		make_employee(
			"test_call_agent_b@example.com", company="_Test Company", cell_number=f"+91{self.number}2"
		)
		schedule = "erpnext.telephony.doctype.call_log.call_log.get_scheduled_employees_for_popup"

		with patch(schedule, return_value=[agent]):
			call_log = frappe.get_doc(
				"Call Log", self._make_call_log(to=f"+91{self.number}1", type="Incoming", status="Ringing")
			)

		# The agent's popup slot ends before the call does.
		call_log.status = "Completed"
		with patch(schedule, return_value=[]), patch.object(frappe, "publish_realtime") as publish:
			call_log.save(ignore_permissions=True)

		ended = [c for c in publish.call_args_list if c.args[0] == f"call_{call_log.id}_ended"]
		self.assertEqual([c.kwargs.get("user") for c in ended], [agent])

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
		contact = frappe.get_doc({"doctype": "Contact", "first_name": f"_Test Caller {self.number}"})
		contact.insert(ignore_permissions=True)
		self._make_call_log(
			to=f"+91{self.number}",
			type="Incoming",
			links=[{"link_doctype": "Contact", "link_name": contact.name}],
		)
		timeline = get_linked_call_logs("Contact", contact.name)
		self.assertEqual(len(timeline), 1)
		self.assertEqual(timeline[0]["template_data"]["to"], f"+91{self.number}")

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
			self.assertEqual(get_linked_call_logs("Contact", contact.name), [])
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

	def test_linking_does_not_commit(self):
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": f"_Test Caller {self.number}",
				"phone_nos": [{"phone": self.number, "is_primary_phone": 1}],
			}
		)
		contact.flags.ignore_auto_link_call_log = True
		contact.insert(ignore_permissions=True)
		call_log = self._make_call_log(**{"from": f"0{self.number}", "type": "Outgoing"})

		contact.flags.ignore_auto_link_call_log = False
		with patch.object(frappe.db, "commit") as commit:
			link_existing_conversations(contact, "Open")

		commit.assert_not_called()
		self.assertIn(
			contact.name,
			frappe.get_all(
				"Dynamic Link",
				filters={"parenttype": "Call Log", "parent": call_log, "link_doctype": "Contact"},
				pluck="link_name",
			),
		)

	def test_call_links_all_contacts_and_leads_with_formatted_numbers(self):
		number = "94" + "".join(random.choices(string.digits, k=8))
		contacts = [
			self._make_contact(f"+91 {number[:5]} {number[5:]}"),
			self._make_contact(f"0{number[:3]}-{number[3:6]}-{number[6:]}"),
		]
		# shares the last 8 digits only
		other_contact = self._make_contact(f"+91 93{number[2:]}")
		lead = frappe.get_doc(
			{"doctype": "Lead", "first_name": f"_Test Caller {number}", "mobile_no": f"(+91) {number}"}
		).insert(ignore_permissions=True)

		call_log = frappe.get_doc(
			"Call Log", self._make_call_log(**{"from": f"+91{number}"}, type="Incoming")
		)
		linked_contacts = {d.link_name for d in call_log.links if d.link_doctype == "Contact"}
		self.assertLessEqual(set(contacts), linked_contacts)
		self.assertNotIn(other_contact, linked_contacts)
		self.assertEqual([d.link_name for d in call_log.links if d.link_doctype == "Lead"], [lead.name])

		short_call = frappe.get_doc(
			"Call Log", self._make_call_log(**{"from": f"0{number[-5:]}"}, type="Incoming")
		)
		self.assertEqual(short_call.links, [])

	def test_call_is_received_by_agent_with_same_number_only(self):
		agent = make_employee(
			"test_call_agent_a@example.com",
			company="_Test Company",
			cell_number=f"+91 {self.number[:5]} {self.number[5:]}",
		)
		make_employee(
			"test_call_agent_b@example.com", company="_Test Company", cell_number=f"1{self.number}5"
		)

		call_log = frappe.get_doc("Call Log", self._make_call_log(to=f"+91{self.number}", type="Incoming"))
		self.assertEqual(call_log.call_received_by, agent)
		self.assertEqual(call_log.get_agent_emails(), {"test_call_agent_a@example.com"})

		short_call = frappe.get_doc("Call Log", self._make_call_log(to=self.number[-4:], type="Incoming"))
		self.assertIsNone(short_call.call_received_by)

	def _make_contact(self, phone):
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": f"_Test Caller {phone}",
				"phone_nos": [{"phone": phone, "is_primary_phone": 1}],
			}
		)
		return contact.insert(ignore_permissions=True).name
