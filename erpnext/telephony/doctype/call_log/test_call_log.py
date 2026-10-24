# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import random
import string

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.telephony.doctype.call_log.call_log import link_existing_conversations
from erpnext.tests.utils import ERPNextTestSuite


class TestCallLog(ERPNextTestSuite):
	def setUp(self):
		self.number = "98" + "".join(random.choices(string.digits, k=8))

	def test_call_links_all_contacts_and_leads_with_formatted_numbers(self):
		number = "94" + "".join(random.choices(string.digits, k=8))
		contacts = [
			self._make_contact(f"+91 {number[:5]} {number[5:]}"),
			self._make_contact(f"0{number[:3]}-{number[3:6]}-{number[6:]}"),
			self._make_contact(f"(+91 {number}) "),
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
			cell_number=f"(+91 {self.number[:5]} {self.number[5:]}) ",
		)
		make_employee(
			"test_call_agent_b@example.com", company="_Test Company", cell_number=f"1{self.number}5"
		)

		call_log = frappe.get_doc("Call Log", self._make_call_log(to=f"+91{self.number}", type="Incoming"))
		self.assertEqual(call_log.call_received_by, agent)

		short_call = frappe.get_doc("Call Log", self._make_call_log(to=self.number[-4:], type="Incoming"))
		self.assertIsNone(short_call.call_received_by)

	def test_new_contact_number_links_past_calls_in_any_format(self):
		call_log = self._make_call_log(**{"from": f"+91{self.number}"}, type="Incoming")
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": f"_Test Caller {self.number}",
				"phone_nos": [{"phone": f"0{self.number[:5]} {self.number[5:]}", "is_primary_phone": 1}],
			}
		)
		contact.flags.ignore_auto_link_call_log = True
		contact.insert(ignore_permissions=True)

		contact.flags.ignore_auto_link_call_log = False
		link_existing_conversations(contact, "Open")

		links = frappe.get_all(
			"Dynamic Link", {"parenttype": "Call Log", "parent": call_log}, pluck="link_name"
		)
		self.assertIn(contact.name, links)

	def _make_call_log(self, **kwargs):
		doc = frappe.get_doc({"doctype": "Call Log", "id": frappe.generate_hash(length=10), **kwargs})
		doc.insert(ignore_permissions=True)
		return doc.name

	def _make_contact(self, phone):
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": f"_Test Caller {phone}",
				"phone_nos": [{"phone": phone, "is_primary_phone": 1}],
			}
		)
		return contact.insert(ignore_permissions=True).name
