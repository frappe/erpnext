# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.buying.doctype.supplier_scorecard.test_supplier_scorecard import make_scorecard_for
from erpnext.buying.doctype.supplier_scorecard_period.supplier_scorecard_period import (
	make_supplier_scorecard,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSupplierScorecardPeriod(ERPNextTestSuite):
	def test_manual_period_is_validated_against_its_scorecard(self):
		scorecard = make_scorecard_for("_Test Supplier SC Manual Period")
		scorecard.insert()
		existing = frappe.get_all(
			"Supplier Scorecard Period",
			filters={"scorecard": scorecard.name, "docstatus": 1},
			fields=["start_date", "end_date"],
			limit=1,
		)[0]

		for start_date, end_date in (
			(add_days(nowdate(), 10), add_days(nowdate(), 5)),
			(existing.start_date, existing.end_date),
		):
			with self.subTest(start_date=start_date, end_date=end_date):
				period = make_manual_period(scorecard.name, start_date, end_date)
				self.assertRaises(frappe.ValidationError, period.insert)

		period = make_manual_period(scorecard.name, add_days(nowdate(), 5), add_days(nowdate(), 10))
		period.insert()
		self.assertEqual(period.supplier, scorecard.supplier)


def make_manual_period(scorecard, start_date, end_date):
	period = make_supplier_scorecard(scorecard)
	period.update({"supplier": "_Test Supplier", "start_date": start_date, "end_date": end_date})
	return period
