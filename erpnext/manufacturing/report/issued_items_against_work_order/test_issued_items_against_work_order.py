# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry, make_stock_return_entry
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.tests.utils import ERPNextTestSuite

STORES = "_Test Warehouse - _TC"


class TestIssuedItemsAgainstWorkOrder(ERPNextTestSuite):
	def setUp(self):
		self.rm_item = make_item(properties={"is_stock_item": 1, "valuation_rate": 100}).name
		self.fg_item = make_item(properties={"is_stock_item": 1}).name
		self.bom = make_bom(item=self.fg_item, raw_materials=[self.rm_item])
		test_stock_entry.make_stock_entry(item_code=self.rm_item, target=STORES, qty=10, basic_rate=100)

	def make_work_order(self, qty, **kwargs):
		return make_wo_order_test_record(
			item=self.fg_item,
			bom_no=self.bom.name,
			qty=qty,
			source_warehouse=STORES,
			wip_warehouse=create_warehouse("_Test Issued Items WIP"),
			**kwargs,
		)

	def make_entry(self, work_order, purpose, qty, consumed_qty=None):
		stock_entry = frappe.get_doc(make_stock_entry(work_order, purpose, qty))
		for row in stock_entry.items:
			if consumed_qty is not None and row.item_code == self.rm_item:
				row.qty = consumed_qty
		stock_entry.submit()

	def issued_qty(self, work_order):
		report = frappe.get_file_json(
			frappe.get_app_path(
				"erpnext",
				"manufacturing",
				"report",
				"issued_items_against_work_order",
				"issued_items_against_work_order.json",
			)
		)
		return sorted(row[4] for row in frappe.db.sql(report["query"]) if row[0] == work_order)

	def test_returned_material_is_shown_as_negative(self):
		work_order = self.make_work_order(2)
		self.make_entry(work_order.name, "Material Transfer for Manufacture", 2)
		self.make_entry(work_order.name, "Manufacture", 2, consumed_qty=1)
		make_stock_return_entry(work_order.name).submit()

		self.assertEqual(self.issued_qty(work_order.name), [-1, 2])
