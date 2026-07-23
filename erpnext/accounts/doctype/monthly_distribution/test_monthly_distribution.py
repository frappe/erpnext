# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import getdate

from erpnext.accounts.doctype.monthly_distribution.monthly_distribution import (
	get_percentage,
	get_periodwise_distribution_data,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestMonthlyDistribution(ERPNextTestSuite):
	"""Monthly Distribution spreads an amount across months. validate() enforces a
	100% total; get_percentage() sums the months that fall inside a period window."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_distribution(self, allocations):
		doc = frappe.new_doc("Monthly Distribution")
		doc.distribution_id = f"_Test MD {frappe.generate_hash(length=6)}"
		for month, pct in allocations:
			doc.append("percentages", {"month": month, "percentage_allocation": pct})
		return doc

	def test_get_months_populates_twelve_even_rows(self):
		doc = frappe.new_doc("Monthly Distribution")
		doc.distribution_id = "_Test MD Even"
		doc.get_months()

		self.assertEqual(len(doc.percentages), 12)
		self.assertEqual(doc.percentages[0].month, "January")
		self.assertEqual(doc.percentages[-1].month, "December")
		self.assertEqual([d.idx for d in doc.percentages], list(range(1, 13)))
		for d in doc.percentages:
			self.assertAlmostEqual(d.percentage_allocation, 100.0 / 12, places=4)
		# the auto-populated rows round to exactly 100 and pass validation
		doc.validate()

	def test_validate_rejects_total_other_than_100(self):
		doc = self.make_distribution([("January", 50), ("February", 30)])  # sums to 80
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_get_percentage_sums_period_window(self):
		doc = self.make_distribution([("January", 50), ("February", 30), ("March", 20)])
		doc.insert()  # total is 100, so validate passes

		# a quarter starting in January covers Jan+Feb+Mar
		self.assertEqual(get_percentage(doc, getdate("2026-01-01"), 3), 100)
		# a single month picks up only that month
		self.assertEqual(get_percentage(doc, getdate("2026-02-01"), 1), 30)
		# months with no row simply contribute 0 (there is no guard that all 12 exist)
		self.assertEqual(get_percentage(doc, getdate("2026-04-01"), 1), 0)

	def test_periodwise_distribution_maps_each_period(self):
		doc = self.make_distribution([("January", 50), ("February", 30), ("March", 20)])
		doc.insert()

		period_list = [
			frappe._dict(key="q1", from_date=getdate("2026-01-01")),
			frappe._dict(key="q2", from_date=getdate("2026-04-01")),
		]
		data = get_periodwise_distribution_data(doc.name, period_list, "Quarterly")
		self.assertEqual(data["q1"], 100)  # Jan+Feb+Mar
		self.assertEqual(data["q2"], 0)  # Apr+May+Jun carry no allocation
