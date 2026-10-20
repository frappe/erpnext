# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee


class TestSMSCenter(IntegrationTestCase):
	def test_all_lead_open_query_selects_mobile_no(self):
		lead = frappe.get_doc(
			{"doctype": "Lead", "lead_name": "SMS Lead", "status": "Open", "mobile_no": "9800000001"}
		).insert()

		sms_center = frappe.new_doc("SMS Center")
		sms_center.send_to = "All Lead (Open)"
		rows = sms_center.get_contact_query_for_all_open_leads().run(as_list=1)

		self.assertIn([lead.lead_name, "9800000001"], rows)

	def test_receiver_nos_split_on_last_separator(self):
		sms_center = frappe.new_doc("SMS Center")
		sms_center.receiver_list = "Anne-Marie Roy - 9800000004\n+91-98000-00005\n9800000006"

		self.assertEqual(sms_center.get_receiver_nos(), ["9800000004", "+91-98000-00005", "9800000006"])
