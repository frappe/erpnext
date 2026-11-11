# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt

from erpnext.selling.doctype.quotation.mapper import make_revision
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

		data = self._run_report()

		# row layout: (lost_reason, lost_quotations, lost_quotations_pct, lost_value, lost_value_pct, currency)
		row_a = next(row for row in data if row[0] == self.reason_a)
		self.assertEqual(row_a[1], 1)
		# with integer division this is 0; with correct division it is a positive fraction
		self.assertGreater(row_a[2], 0)
		self.assertLess(row_a[2], 100)

	def test_lost_quotation_versions_are_counted_once(self):
		lost_quotations_before = self._count_lost_quotations()
		quotation = make_quotation(company=self.company, qty=1, rate=100)
		revision = make_revision(quotation.name)
		revision.insert()
		revision.submit()

		revision.declare_enquiry_lost([{"lost_reason": self.reason_a}], [])

		self.assertEqual(self._count_lost_quotations(), lost_quotations_before + 1)

	def test_duplicate_reason_counts_value_once(self):
		# the same reason twice on one quotation must not double its lost value
		reason = self._ensure_lost_reason("_Test Lost Reason Dup")
		qo = make_quotation(company=self.company, qty=1, rate=100)
		qo.declare_enquiry_lost([{"lost_reason": reason}], [])
		qo.reload()
		qo.append("lost_reasons", {"lost_reason": reason})
		qo.save()

		row = next(row for row in self._run_report() if row[0] == reason)
		self.assertEqual(row[1], 1)
		self.assertEqual(flt(row[3]), 100)

	def test_value_is_split_across_reasons(self):
		# a quotation lost for two reasons splits its value evenly between them
		reason_x = self._ensure_lost_reason("_Test Lost Reason X")
		reason_y = self._ensure_lost_reason("_Test Lost Reason Y")
		qo = make_quotation(company=self.company, qty=1, rate=100)
		qo.declare_enquiry_lost([{"lost_reason": reason_x}, {"lost_reason": reason_y}], [])

		data = self._run_report()
		self.assertEqual(flt(next(row for row in data if row[0] == reason_x)[3]), 50)
		self.assertEqual(flt(next(row for row in data if row[0] == reason_y)[3]), 50)

	def _run_report(self):
		return execute(
			frappe._dict({"company": self.company, "timespan": "This Year", "group_by": "Lost Reason"})
		)[1]

	def _count_lost_quotations(self):
		return sum(row[1] for row in self._run_report())

	def _ensure_lost_reason(self, name):
		if not frappe.db.exists("Quotation Lost Reason", name):
			frappe.get_doc({"doctype": "Quotation Lost Reason", "order_lost_reason": name}).insert()
		return name

	def _make_lost_quotation(self, reason):
		qo = make_quotation(company=self.company, qty=1, rate=100)
		qo.declare_enquiry_lost([{"lost_reason": reason}], [])
		return qo

	def test_permission_scopes_rows_and_summary(self):
		# a user permission that hides one lost quotation must drop it from the rows, the
		# percentages and both summary cards
		territory_visible = self._ensure_territory("_Test Lost Territory Visible")
		territory_hidden = self._ensure_territory("_Test Lost Territory Hidden")
		reason_visible = self._ensure_lost_reason("_Test Lost Reason Perm Visible")
		reason_hidden = self._ensure_lost_reason("_Test Lost Reason Perm Hidden")

		self._make_lost_quotation_in(territory_visible, reason_visible, rate=100)
		self._make_lost_quotation_in(territory_hidden, reason_hidden, rate=300)

		user = "_test_lost_quotations_perm@example.com"
		if not frappe.db.exists("User", user):
			u = frappe.new_doc("User")
			u.email = user
			u.first_name = "Lost Quotations Perm"
			u.append("roles", {"role": "Sales User"})
			u.insert()
		frappe.permissions.add_user_permission("Territory", territory_visible, user)

		frappe.set_user(user)
		try:
			_columns, data, _msg, _chart, summary = execute(
				frappe._dict({"company": self.company, "timespan": "This Year", "group_by": "Lost Reason"})
			)
		finally:
			frappe.set_user("Administrator")

		reasons = {row[0] for row in data}
		self.assertIn(reason_visible, reasons)
		self.assertNotIn(reason_hidden, reasons)

		# only the visible quotation counts, so its reason is 100% of the user's lost quotations
		row = next(row for row in data if row[0] == reason_visible)
		self.assertEqual(row[1], 1)
		self.assertEqual(flt(row[2]), 100)

		# both summary cards reflect only the visible quotation (count 1, value 100 not 400)
		summary_by_label = {card["label"]: card["value"] for card in summary}
		self.assertEqual(summary_by_label["Total Lost Quotations"], 1)
		self.assertEqual(flt(summary_by_label["Total Lost Value"]), 100)

	def _ensure_territory(self, name):
		if not frappe.db.exists("Territory", name):
			frappe.get_doc(
				doctype="Territory", territory_name=name, parent_territory="All Territories", is_group=0
			).insert()
		return name

	def _make_lost_quotation_in(self, territory, reason, rate=100):
		qo = make_quotation(company=self.company, qty=1, rate=rate)
		qo.declare_enquiry_lost([{"lost_reason": reason}], [])
		# pin territory last so the stored value drives the user-permission filter
		frappe.db.set_value("Quotation", qo.name, "territory", territory)
		return qo
