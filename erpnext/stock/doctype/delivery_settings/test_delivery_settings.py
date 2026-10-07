# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestDeliverySettings(ERPNextTestSuite):
	def test_negative_stop_delay_is_rejected(self):
		settings = frappe.get_doc("Delivery Settings")
		settings.stop_delay = -30
		self.assertRaises(frappe.NonNegativeError, settings.save)
