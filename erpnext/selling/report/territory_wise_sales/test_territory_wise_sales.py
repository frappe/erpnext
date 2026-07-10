# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.doctype.quotation.test_quotation import make_quotation
from erpnext.selling.report.territory_wise_sales.territory_wise_sales import execute
from erpnext.tests.utils import ERPNextTestSuite

TERRITORY = "_Test Territory"


class TestTerritoryWiseSales(ERPNextTestSuite):
	"""The report walks the Opportunity -> Quotation -> Sales Order -> Sales Invoice
	funnel and totals each stage's amount per territory.

	These tests cover the Opportunity and Quotation stages; the Sales Order and
	Sales Invoice (order_amount / billing_amount) stages are not yet exercised."""

	def make_opportunity(self, amount=5000):
		return frappe.get_doc(
			{
				"doctype": "Opportunity",
				"opportunity_from": "Customer",
				"party_name": "_Test Customer",
				"territory": TERRITORY,
				"company": "_Test Company",
				"currency": "INR",
				"opportunity_amount": amount,
				"transaction_date": "2026-06-01",
			}
		).insert()

	def make_quotation_for(self, opportunity, qty, rate):
		qo = make_quotation(item="_Test Item", qty=qty, rate=rate, do_not_save=True)
		qo.opportunity = opportunity.name
		qo.insert()
		qo.submit()
		return qo

	def amount_for(self, territory, field):
		for row in execute(frappe._dict({"company": "_Test Company"}))[1]:
			if row["territory"] == territory:
				return row[field]
		return 0

	def test_opportunity_amount_grouped_by_territory(self):
		before = self.amount_for(TERRITORY, "opportunity_amount")
		opp = self.make_opportunity(5000)
		self.assertEqual(opp.territory, TERRITORY)

		after = self.amount_for(TERRITORY, "opportunity_amount")
		self.assertEqual(after - before, 5000)

	def test_quotation_amount_flows_from_opportunity(self):
		before = self.amount_for(TERRITORY, "quotation_amount")

		opp = self.make_opportunity()
		quotation = self.make_quotation_for(opp, qty=2, rate=500)

		after = self.amount_for(TERRITORY, "quotation_amount")
		self.assertEqual(after - before, quotation.base_grand_total)
