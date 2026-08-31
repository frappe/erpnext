# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.doctype.quotation.test_quotation import make_quotation
from erpnext.selling.report.lost_quotations.lost_quotations import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestLostQuotations(ERPNextTestSuite):
	def setUp(self):
		self.company = "_Test Company"
		self.reason_a = self._ensure_lost_reason("_Test Lost Reason A")
		self.reason_b = self._ensure_lost_reason("_Test Lost Reason B")

	def test_lost_quotations_percentage_is_not_integer_divided(self):
		# `lost_quotations_pct` is count(group) / count(total) * 100. count/count is integer division on
		# Postgres, which truncates a proper fraction to 0; this asserts the percentage stays fractional.
		# reason A on one quotation, reason B on three -> A is a strict minority of the total
		self._make_lost_quotation(self.reason_a)
		for _ in range(3):
			self._make_lost_quotation(self.reason_b)

		_columns, data = execute(
			frappe._dict({"company": self.company, "timespan": "This Year", "group_by": "Lost Reason"})
		)

		# row layout: (lost_reason, lost_quotations, lost_quotations_pct, lost_value, lost_value_pct)
		row_a = next(row for row in data if row[0] == self.reason_a)
		self.assertEqual(row_a[1], 1)
		# with integer division this is 0; with correct division it is a positive fraction
		self.assertGreater(row_a[2], 0)
		self.assertLess(row_a[2], 100)

	def _ensure_lost_reason(self, name):
		if not frappe.db.exists("Quotation Lost Reason", name):
			frappe.get_doc({"doctype": "Quotation Lost Reason", "order_lost_reason": name}).insert()
		return name

	def _make_lost_quotation(self, reason):
		qo = make_quotation(company=self.company, qty=1, rate=100)
		qo.declare_enquiry_lost([{"lost_reason": reason}], [])
		return qo
