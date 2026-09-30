# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestAuthorizationRule(ERPNextTestSuite):
	def test_duplicate_rule_is_blocked(self):
		"""check_duplicate_entry uses frappe.get_all over Authorization Rule; a second rule with the
		same transaction/based_on/approving_role/value must be rejected as a duplicate (the converted
		query must find the existing row on both engines)."""

		def make_rule():
			return frappe.get_doc(
				{
					"doctype": "Authorization Rule",
					"transaction": "Sales Order",
					"based_on": "Grand Total",
					"approving_role": "Sales Manager",
					"value": 100000,
				}
			)

		make_rule().insert(ignore_permissions=True)
		# a second identical rule must be caught by the converted duplicate-check query
		self.assertRaises(frappe.ValidationError, make_rule().insert, ignore_permissions=True)
