# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.report.warehouse_wise_stock_balance.warehouse_wise_stock_balance import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestWarehouseWiseStockBalance(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company", **extra})
		return execute(filters)[1]

	def row(self, data, warehouse):
		return next(w for w in data if w["name"] == warehouse)

	def test_disabled_warehouses_with_stock_stay_in_the_totals(self):
		group = create_warehouse("_Test WWSB Disabled Group", properties={"is_group": 1})
		child = create_warehouse("_Test WWSB Disabled Child", properties={"parent_warehouse": group})
		make_stock_entry(item_code="_Test Item", to_warehouse=child, qty=5, rate=100)
		frappe.db.set_value("Warehouse", group, "disabled", 1)
		root = frappe.db.get_value("Warehouse", group, "parent_warehouse")

		data = self.run_report()
		with_disabled = self.run_report(show_disabled_warehouses=1)

		self.assertEqual(
			self.row(data, root)["stock_balance"], self.row(with_disabled, root)["stock_balance"]
		)
		self.assertEqual(self.row(data, child)["indent"], self.row(with_disabled, child)["indent"])

	def test_empty_disabled_warehouse_shows_only_when_asked(self):
		empty = create_warehouse("_Test WWSB Empty Disabled")
		frappe.db.set_value("Warehouse", empty, "disabled", 1)

		self.assertNotIn(empty, [row["name"] for row in self.run_report()])
		self.assertIn(empty, [row["name"] for row in self.run_report(show_disabled_warehouses=1)])
