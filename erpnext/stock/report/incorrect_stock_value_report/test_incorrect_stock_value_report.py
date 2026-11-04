# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.report.incorrect_stock_value_report.incorrect_stock_value_report import execute

COMPANY = "_Test Company with perpetual inventory"


class TestIncorrectStockValueReport(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def run_report(self, **extra):
		filters = frappe._dict(
			company=COMPANY,
			from_date="2026-01-01",
			to_date="2026-12-31",
		)
		filters.update(extra)
		return list(execute(filters)[1])

	def test_account_is_required(self):
		self.assertRaises(frappe.MandatoryError, self.run_report)
