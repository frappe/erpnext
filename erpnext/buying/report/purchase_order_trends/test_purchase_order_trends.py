# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
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

	def test_restricted_user_sees_only_permitted_orders(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.purchase_order_trends.purchase_order_trends import execute
		from erpnext.stock.doctype.item.test_item import create_item

		item = create_item("_Test PO Trends Permission Item").name
		create_purchase_order(item_code=item, supplier="_Test Supplier", qty=3, rate=100)
		create_purchase_order(item_code=item, supplier="_Test Supplier 1", qty=5, rate=100)
		user = create_user("po_trends_restricted@example.com", "Purchase User").name
		add_user_permission("Supplier", "_Test Supplier", user)

		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": get_fiscal_year(today())[0],
				"period": "Monthly",
				"based_on": "Item",
			}
		)
		with self.set_user(user):
			data = execute(filters)[1]

		item_row = next(row for row in data if row[0] == item)
		self.assertEqual(item_row[-2:], [3, 300])

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

	def test_based_on_project_leaves_out_rows_without_a_project(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.purchase_order_trends.purchase_order_trends import execute
		from erpnext.projects.doctype.project.test_project import make_project

		project = make_project({"project_name": "_Test PO Trends Project"}).name
		po = create_purchase_order(qty=2, rate=100, transaction_date=today(), do_not_save=True)
		po.items[0].project = project
		po.insert().submit()
		create_purchase_order(qty=3, rate=100, transaction_date=today())

		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": get_fiscal_year(today())[0],
				"period": "Monthly",
				"based_on": "Project",
			}
		)

		projects = [row[0] for row in execute(filters)[1]]
		self.assertIn(project, projects)
		self.assertTrue(all(projects))
