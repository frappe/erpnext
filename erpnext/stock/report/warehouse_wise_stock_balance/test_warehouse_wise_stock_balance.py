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

	def test_balance_and_parent_accumulation(self):
		parent = create_warehouse("_Test WWSB Parent", properties={"is_group": 1})
		child = create_warehouse("_Test WWSB Child", properties={"parent_warehouse": parent})

		make_stock_entry(item_code="_Test Item", to_warehouse=child, qty=10, rate=100)

		data = self.run_report()
		# stock balance = sum of stock value difference (10 * 100)
		self.assertEqual(self.row(data, child)["stock_balance"], 1000)
		# the group warehouse rolls up its children
		self.assertEqual(self.row(data, parent)["stock_balance"], 1000)
