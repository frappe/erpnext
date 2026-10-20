# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.accounts.report.share_ledger.share_ledger import execute


class TestShareLedger(IntegrationTestCase):
	def test_link_filters_reject_operator_lists(self):
		with self.assertRaises(frappe.ValidationError):
			execute({"company": ["!=", ""]})
