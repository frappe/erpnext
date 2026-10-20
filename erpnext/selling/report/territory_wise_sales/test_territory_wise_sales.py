# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.doctype.quotation.test_quotation import make_quotation
from erpnext.selling.report.territory_wise_sales.territory_wise_sales import execute
from erpnext.tests.utils import ERPNextTestSuite

TERRITORY = "_Test Territory"


class TestTerritoryWiseSales(ERPNextTestSuite):
	"""The report walks the Opportunity -> Quotation -> Sales Order -> Sales Invoice
	funnel and totals each stage's amount per territory."""

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

	def make_quotation_for(self, opportunity, qty, rate, item="_Test Item"):
		qo = make_quotation(item=item, qty=qty, rate=rate, do_not_save=True)
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

	def test_opportunity_amount_uses_company_currency(self):
		before = self.amount_for(TERRITORY, "opportunity_amount")

		opp = frappe.get_doc(
			{
				"doctype": "Opportunity",
				"opportunity_from": "Customer",
				"party_name": "_Test Customer",
				"territory": TERRITORY,
				"company": "_Test Company",
				"currency": "USD",
				"conversion_rate": 70,
				"opportunity_amount": 100,
				"transaction_date": "2026-06-01",
			}
		).insert()

		after = self.amount_for(TERRITORY, "opportunity_amount")
		# 100 in the opportunity's currency must show as 7000 in company currency
		self.assertEqual(opp.conversion_rate, 70)
		self.assertEqual(after - before, 7000)

	def test_order_and_billing_amount_counted_once(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

		order_before = self.amount_for(TERRITORY, "order_amount")
		billing_before = self.amount_for(TERRITORY, "billing_amount")

		opp = self.make_opportunity()
		quotation = make_quotation(
			item_list=[
				{"item_code": "_Test Item", "qty": 1, "rate": 500, "warehouse": "_Test Warehouse - _TC"},
				{"item_code": "_Test Item 2", "qty": 1, "rate": 500, "warehouse": "_Test Warehouse - _TC"},
			],
			do_not_save=True,
		)
		quotation.opportunity = opp.name
		quotation.insert()
		quotation.submit()

		so = make_sales_order(quotation.name)
		so.delivery_date = frappe.utils.add_days(frappe.utils.nowdate(), 7)
		so.insert()
		so.submit()

		si = make_sales_invoice(so.name)
		si.insert()
		si.submit()

		order_after = self.amount_for(TERRITORY, "order_amount")
		billing_after = self.amount_for(TERRITORY, "billing_amount")

		# two item rows must not multiply the parent total
		self.assertEqual(order_after - order_before, so.base_grand_total)
		self.assertEqual(billing_after - billing_before, si.base_grand_total)

	def test_order_from_merged_quotations_counted_once(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		before = self.amount_for(TERRITORY, "order_amount")

		opp1 = self.make_opportunity()
		opp2 = self.make_opportunity()
		q1 = self.make_quotation_for(opp1, qty=1, rate=500)
		q2 = self.make_quotation_for(opp2, qty=1, rate=500, item="_Test Item 2")

		so = make_sales_order(q1.name)
		so = make_sales_order(q2.name, so)
		so.delivery_date = frappe.utils.add_days(frappe.utils.nowdate(), 7)
		so.insert()
		so.submit()

		after = self.amount_for(TERRITORY, "order_amount")
		# an order built from two quotations in the territory must count once
		self.assertEqual(after - before, so.base_grand_total)
