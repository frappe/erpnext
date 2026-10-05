# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission

from erpnext.buying.report.supplier_quotation_comparison.supplier_quotation_comparison import execute
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
ITEM = "_Test Item"


class TestSupplierQuotationComparison(ERPNextTestSuite):
	def make_quotation(self, supplier, qty, rate, currency="INR", conversion_rate=1):
		sq = frappe.get_doc(
			{
				"doctype": "Supplier Quotation",
				"supplier": supplier,
				"company": COMPANY,
				"currency": currency,
				"conversion_rate": conversion_rate,
				"transaction_date": "2026-06-01",
				"items": [
					{"item_code": ITEM, "qty": qty, "rate": rate, "warehouse": "_Test Warehouse - _TC"}
				],
			}
		)
		sq.insert()
		sq.submit()
		return sq

	def run_report(self, **extra):
		return self.execute_report(**extra)[1]

	def execute_report(self, **extra):
		filters = frappe._dict({"company": COMPANY, "from_date": "2026-01-01", "to_date": "2026-12-31"})
		filters.update(extra)
		return execute(filters)

	def test_cheapest_quote_is_compared_in_company_currency(self):
		rupee_quote = self.make_quotation("_Test Supplier", qty=10, rate=500)
		dollar_quote = self.make_quotation(
			"_Test Supplier 1", qty=10, rate=10, currency="USD", conversion_rate=80
		)

		cheapest = {row["quotation"] for row in self.run_report(item_code=ITEM) if row.get("min")}
		self.assertIn(rupee_quote.name, cheapest)
		self.assertNotIn(dollar_quote.name, cheapest)

	@ERPNextTestSuite.change_settings("Buying Settings", {"allow_zero_qty_in_supplier_quotation": 1})
	def test_unit_price_quote_is_compared_by_rate(self):
		quantity_quote = self.make_quotation("_Test Supplier", qty=10, rate=500)
		unit_price_quote = self.make_quotation("_Test Supplier 1", qty=0, rate=900)

		rows = {row["quotation"]: row for row in self.run_report(item_code=ITEM)}
		self.assertEqual(rows[unit_price_quote.name]["price_per_unit"], 900)
		self.assertTrue(rows[quantity_quote.name].get("min"))
		self.assertFalse(rows[unit_price_quote.name].get("min"))

	def test_supplier_restricted_user_sees_only_that_suppliers_quotes(self):
		own_quote = self.make_quotation("_Test Supplier", qty=10, rate=500)
		self.make_quotation("_Test Supplier 1", qty=10, rate=450)
		user = create_user("sq-comparison-buyer@example.com", "Purchase User")
		add_user_permission("Supplier", "_Test Supplier", user.name)

		with self.set_user(user.name):
			_columns, data, _message, chart = self.execute_report(
				item_code=ITEM, categorize_by="Categorize by Supplier"
			)

		self.assertEqual({row["quotation"] for row in data}, {own_quote.name})
		self.assertEqual(chart["data"]["labels"], ["_Test Supplier"])
