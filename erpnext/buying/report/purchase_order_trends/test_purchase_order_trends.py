# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

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
