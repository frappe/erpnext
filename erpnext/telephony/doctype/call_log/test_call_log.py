# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import random
import string
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee


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
