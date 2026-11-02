# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.report.voucher_wise_balance.voucher_wise_balance import execute


class TestVoucherWiseBalance(FrappeTestCase):
	def test_company_is_mandatory(self):
		self.assertRaises(frappe.ValidationError, execute, frappe._dict(from_date="2026-01-01"))
