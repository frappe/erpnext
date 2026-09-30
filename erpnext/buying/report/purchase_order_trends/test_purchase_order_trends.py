# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import today

from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestPurchaseOrderTrends(ERPNextTestSuite):
	def test_supplier_with_divergent_stored_name_stays_one_row(self):
		# supplier_name is a stored per-transaction field; historical purchase docs can hold a different
		# value for the same supplier. trends groups by t1.supplier only and aggregates supplier_name with
		# Max(), so the report stays one row per supplier on both MariaDB and Postgres. Grouping by
		# supplier_name (the pre-fix behaviour) would split the supplier into two rows.
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.purchase_order_trends.purchase_order_trends import execute

		create_purchase_order(supplier="_Test Supplier", qty=3, rate=100)
		po2 = create_purchase_order(supplier="_Test Supplier", qty=2, rate=100)
		# simulate a historical doc that stored a different supplier_name for the same supplier
		frappe.db.set_value("Purchase Order", po2.name, "supplier_name", "_Test Supplier (renamed)")

		filters = {
			"company": "_Test Company",
			"period": "Monthly",
			"based_on": "Supplier",
		}
		columns, data, _chart_none, _chart = execute(filters)

		self.assertTrue(columns)
		supplier_rows = [row for row in data if row[0] == "_Test Supplier"]
		self.assertEqual(len(supplier_rows), 1)

	def test_total_row_not_double_counted_in_chart(self):
		# Regression test for the fix in trends.calculate_total_row that populates the
		# Total row's Currency column. Before the fix in get_chart_data (skipping the
		# Total row by label instead of `if not row[start]`), that populated Currency
		# cell made the Total-row-skip guard falsy, so the already-summed Total row got
		# added into the chart a second time (a PO of qty=3, rate=100 -> 300 read as 600).
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.purchase_order_trends.purchase_order_trends import execute

		create_purchase_order(supplier="_Test Supplier", qty=3, rate=100, transaction_date=today())

		fiscal_year = get_fiscal_year(today())[0]

		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": fiscal_year,
				"period": "Monthly",
				"based_on": "Item",
			}
		)

		columns, data, _message, chart = execute(filters)

		self.assertTrue(columns)
		self.assertTrue(data)

		# The Total row (present in `data`) must not be re-summed into the chart's datapoints.
		total_row = next(row for row in data if row[0] == f"'{_('Total')}'")
		expected_total = total_row[-1]  # Total(Amt) is the last column

		chart_total = sum(chart["data"]["datasets"][0]["values"])

		self.assertEqual(chart_total, expected_total)
		self.assertEqual(chart_total, 300)

	def test_chart_currency_matches_company_currency(self):
		# Regression test: the chart's "currency" key should reflect the transacting
		# company's currency (conditions["company_currency"]), not a stale global default.
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.purchase_order_trends.purchase_order_trends import execute

		create_purchase_order(supplier="_Test Supplier", qty=1, rate=100, transaction_date=today())

		fiscal_year = get_fiscal_year(today())[0]

		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": fiscal_year,
				"period": "Monthly",
				"based_on": "Item",
			}
		)

		_columns, _data, _message, chart = execute(filters)

		expected_currency = frappe.get_cached_value("Company", "_Test Company", "default_currency")
		self.assertEqual(chart["currency"], expected_currency)

	def test_group_by_chart_matches_table_total_with_mixed_group_sizes(self):
		# _Test Item is split across two suppliers -> two detail rows under one header row.
		# _Test Item 2 has only one supplier -> exactly one detail row under its header row.
		# A regression that double-counts header rows would inflate the chart above 600;
		# a regression that zeroes single-group rows would report less than 600.
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.purchase_order_trends.purchase_order_trends import execute

		create_purchase_order(
			item_code="_Test Item", supplier="_Test Supplier", qty=3, rate=100, transaction_date=today()
		)
		create_purchase_order(
			item_code="_Test Item", supplier="_Test Supplier 1", qty=2, rate=100, transaction_date=today()
		)
		create_purchase_order(
			item_code="_Test Item 2", supplier="_Test Supplier", qty=1, rate=100, transaction_date=today()
		)

		fiscal_year = get_fiscal_year(today())[0]
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": fiscal_year,
				"period": "Monthly",
				"based_on": "Item",
				"group_by": "Supplier",
			}
		)

		columns, data, _message, chart = execute(filters)
		self.assertTrue(columns)
		self.assertTrue(data)

		total_row = next(row for row in data if row[0] == f"'{_('Total')}'")
		expected_total = total_row[-1]
		chart_total = sum(chart["data"]["datasets"][0]["values"])

		# 300 (item/supplier) + 200 (item/supplier1) + 100 (item2/supplier) = 600
		self.assertEqual(expected_total, 600)
		self.assertEqual(chart_total, expected_total)

	def test_group_by_swapped_roles_based_on_supplier_group_by_item(self):
		# Same regression, opposite role assignment: based_on="Supplier" with group_by="Item".
		# Supplier's based_on_cols (Supplier, Supplier Name, Supplier Group, Currency) put the
		# group_by placeholder at a different column index than the Item-based_on case above,
		# exercising the alternate `inc`/`ind` arithmetic.
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.purchase_order_trends.purchase_order_trends import execute

		create_purchase_order(
			item_code="_Test Item", supplier="_Test Supplier", qty=3, rate=100, transaction_date=today()
		)
		create_purchase_order(
			item_code="_Test Item 2", supplier="_Test Supplier", qty=1, rate=100, transaction_date=today()
		)

		fiscal_year = get_fiscal_year(today())[0]
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": fiscal_year,
				"period": "Monthly",
				"based_on": "Supplier",
				"group_by": "Item",
			}
		)

		columns, data, _message, chart = execute(filters)
		total_row = next(row for row in data if row[0] == f"'{_('Total')}'")
		expected_total = total_row[-1]
		chart_total = sum(chart["data"]["datasets"][0]["values"])

		# 300 + 100 = 400
		self.assertEqual(expected_total, 400)
		self.assertEqual(chart_total, expected_total)

	def test_group_by_single_group_value_not_zeroed(self):
		# Isolates the specific failure mode flagged in review: a based_on value with exactly
		# one associated group value must still contribute its real amount to the chart, not 0.
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.purchase_order_trends.purchase_order_trends import execute

		create_purchase_order(
			item_code="_Test Item", supplier="_Test Supplier", qty=2, rate=150, transaction_date=today()
		)

		fiscal_year = get_fiscal_year(today())[0]
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": fiscal_year,
				"period": "Monthly",
				"based_on": "Item",
				"group_by": "Supplier",
			}
		)

		columns, data, _message, chart = execute(filters)
		chart_total = sum(chart["data"]["datasets"][0]["values"])

		self.assertGreater(chart_total, 0)
		self.assertEqual(chart_total, 300)
