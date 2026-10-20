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
