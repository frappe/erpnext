# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestDeliverySettings(ERPNextTestSuite):
	def test_negative_stop_delay_is_rejected(self):
		settings = frappe.get_doc("Delivery Settings")
		settings.stop_delay = -30
		self.assertRaises(frappe.NonNegativeError, settings.save)

	def test_dispatch_attachment_must_be_delivery_note_print_format(self):
		print_format = frappe.db.get_value("Print Format", {"doc_type": ("!=", "Delivery Note")}, "name")
		settings = frappe.get_doc("Delivery Settings")
		settings.dispatch_attachment = print_format
		self.assertRaises(frappe.ValidationError, settings.save)
