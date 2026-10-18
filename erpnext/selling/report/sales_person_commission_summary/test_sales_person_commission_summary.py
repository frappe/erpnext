# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.report.sales_person_commission_summary.sales_person_commission_summary import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSalesPersonCommissionSummary(ERPNextTestSuite):
	"""The report joins a sales document (Sales Invoice/Order/Delivery Note) with its
	Sales Team rows, listing each sales person's contribution and commission."""

	def setUp(self):
		# reuse the bootstrap sales persons (under the "Sales Team" group)
		self.sales_person = "_Test Sales Person"

	def make_invoice_with_commission(self, percentage=100, commission_rate=5, incentives=50):
		si = create_sales_invoice(rate=1000, qty=1, do_not_save=True, posting_date="2026-06-01")
		si.append(
			"sales_team",
			{
				"sales_person": self.sales_person,
				"allocated_percentage": percentage,
				"commission_rate": commission_rate,
				"incentives": incentives,
			},
		)
		si.insert()
		si.submit()
		si.reload()  # reflect any values recomputed on submit
		return si

	def make_invoice_split_between_two_sales_persons(self):
		si = create_sales_invoice(rate=1000, qty=1, do_not_save=True, posting_date="2026-06-01")
		si.append(
			"sales_team",
			{
				"sales_person": "_Test Sales Person",
				"allocated_percentage": 60,
				"commission_rate": 5,
				"incentives": 60,
			},
		)
		si.append(
			"sales_team",
			{
				"sales_person": "_Test Sales Person 1",
				"allocated_percentage": 40,
				"commission_rate": 5,
				"incentives": 20,
			},
		)
		si.insert()
		si.submit()
		si.reload()
		return si

	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"doc_type": "Sales Invoice",
				"sales_person": self.sales_person,
				# scope to this test's posting date so the query isn't unbounded over
				# every invoice for the shared sales person
				"from_date": "2026-06-01",
				"to_date": "2026-06-01",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_doc_type_is_mandatory(self):
		self.assertRaises(frappe.ValidationError, execute, frappe._dict({"company": "_Test Company"}))

	def test_commission_row_matches_sales_team_entry(self):
		si = self.make_invoice_with_commission(percentage=100, commission_rate=5, incentives=50)
		team = si.sales_team[0]

		rows = self.run_report()
		row = next((r for r in rows if r[0] == si.name), None)
		self.assertIsNotNone(row, "Invoice with commission missing from report")

		# row: name, customer, territory, posting_date, base_net_amount, sales_person,
		#      allocated_percentage, commission_rate, allocated_amount, incentives
		self.assertEqual(row[1], si.customer)
		self.assertEqual(row[4], si.base_net_total)
		self.assertEqual(row[5], self.sales_person)
		self.assertEqual(row[6], team.allocated_percentage)
		self.assertEqual(row[7], team.commission_rate)
		self.assertEqual(row[8], team.allocated_amount)
		self.assertEqual(row[9], team.incentives)

	def test_amount_shown_once_per_document(self):
		# amount is the whole document total; it must appear on only the first row of each
		# document so the total row doesn't count it once per sales person
		si = self.make_invoice_split_between_two_sales_persons()
		doc_rows = [r for r in self.run_report(sales_person="Sales Team") if r[0] == si.name]
		self.assertEqual(len(doc_rows), 2)
		self.assertEqual(doc_rows[0][4], si.base_net_total)
		self.assertIsNone(doc_rows[1][4])

	def test_group_sales_person_filter_includes_members(self):
		# filtering on a group (team) must include every descendant sales person's rows
		si = self.make_invoice_with_commission()
		rows = self.run_report(sales_person="Sales Team")
		self.assertIn(si.name, {r[0] for r in rows if r[0]})

	def test_sales_person_filter_scopes_rows(self):
		si = self.make_invoice_with_commission()

		filtered = self.run_report(sales_person="_Test Sales Person 1")
		self.assertNotIn(si.name, {r[0] for r in filtered if r[0]})
