# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe

from erpnext.telephony.doctype.call_log.call_log import add_call_summary_and_call_type
from erpnext.tests.utils import ERPNextTestSuite


class TestTelephonyCallType(ERPNextTestSuite):
	def test_only_submitted_call_types_can_be_set_on_a_call(self):
		call_log = frappe.get_doc(
			{"doctype": "Call Log", "id": frappe.generate_hash(length=10), "type": "Outgoing"}
		).insert()
		call_type = frappe.get_doc(
			{
				"doctype": "Telephony Call Type",
				"call_type": "_Test Call Type " + frappe.generate_hash(length=6),
			}
		).insert()

		self.assertRaises(
			frappe.ValidationError, add_call_summary_and_call_type, call_log.name, "draft", call_type.name
		)

		call_type.submit()
		add_call_summary_and_call_type(call_log.name, "submitted", call_type.name)
		self.assertEqual(frappe.db.get_value("Call Log", call_log.name, "type_of_call"), call_type.name)
