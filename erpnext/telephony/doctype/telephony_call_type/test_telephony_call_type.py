# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import os

import frappe
from frappe.model.meta import Meta
from frappe.permissions import get_role_permissions

from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.telephony.doctype.call_log.call_log import add_call_summary_and_call_type
from erpnext.tests.utils import ERPNextTestSuite


class TestTelephonyCallType(ERPNextTestSuite):
	def test_call_popup_users_can_search_call_types(self):
		user = "call-type-employee@example.com"
		make_employee(user, company="_Test Company")

		# read the definition from the file: the test site's permissions come from its last migrate
		definition = frappe.get_file_json(os.path.join(os.path.dirname(__file__), "telephony_call_type.json"))
		meta = Meta(frappe.get_doc(definition))
		frappe.local.role_permissions = {}
		permissions = get_role_permissions(meta, user=user)

		self.assertTrue(permissions.get("select"))
		self.assertTrue(permissions.get("read"))

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
