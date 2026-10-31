# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, now_datetime

from erpnext.crm.utils import update_modified_timestamp
from erpnext.tests.utils import ERPNextTestSuite


class TestCRMSettings(ERPNextTestSuite):
	def make_settings(self, **fields):
		doc = frappe.new_doc("CRM Settings")
		doc.update(fields)
		return doc

	@ERPNextTestSuite.change_settings("CRM Settings", {"update_timestamp_on_new_communication": 1})
	def test_new_communication_updates_timestamp_only_on_lead_and_opportunity(self):
		lead = frappe.get_doc({"doctype": "Lead", "lead_name": "_Test Timestamp Lead"}).insert()
		old_timestamp = add_days(now_datetime(), -30)
		for doctype, name in (("Lead", lead.name), ("Customer", "_Test Customer")):
			frappe.db.set_value(doctype, name, "modified", old_timestamp, update_modified=False)
			update_modified_timestamp(
				frappe._dict(reference_doctype=doctype, reference_name=name, sent_or_received="Received"),
				"after_insert",
			)

		self.assertGreater(frappe.db.get_value("Lead", lead.name, "modified"), old_timestamp)
		self.assertEqual(frappe.db.get_value("Customer", "_Test Customer", "modified"), old_timestamp)

	def test_default_quotation_validity_days_must_be_a_whole_number(self):
		for value in ("30 days", "-10", "1.5"):
			doc = self.make_settings(default_valid_till=value)
			self.assertRaises(frappe.ValidationError, doc.validate_default_valid_till)

		for value in ("30", "0", ""):
			self.make_settings(default_valid_till=value).validate_default_valid_till()
