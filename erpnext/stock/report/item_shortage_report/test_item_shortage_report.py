# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.report.item_shortage_report.item_shortage_report import (
	execute as item_shortage_report,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestItemShortageReport(ERPNextTestSuite):
	def test_item_shortage_report(self):
		item = make_item().name
		so = make_sales_order(item_code=item)

		reserved_qty, projected_qty = frappe.db.get_value(
			"Bin",
			{
				"item_code": item,
				"warehouse": so.items[0].warehouse,
			},
			["reserved_qty", "projected_qty"],
		)
		self.assertEqual(reserved_qty, so.items[0].qty)
		self.assertEqual(projected_qty, -(so.items[0].qty))

		filters = {
			"company": so.company,
		}
		report_data = item_shortage_report(filters)[1]
		item_code_list = [row.get("item_code") for row in report_data]
		self.assertIn(item, item_code_list)

		filters = {
			"company": so.company,
			"warehouse": [so.items[0].warehouse],
		}
		report_data = item_shortage_report(filters)[1]
		item_code_list = [row.get("item_code") for row in report_data]
		self.assertIn(item, item_code_list)

		filters = {
			"company": so.company,
			"warehouse": ["Work In Progress - _TC"],
		}
		report_data = item_shortage_report(filters)[1]
		item_code_list = [row.get("item_code") for row in report_data]
		self.assertNotIn(item, item_code_list)

	def test_group_warehouse_includes_its_warehouses(self):
		item = make_item().name
		so = make_sales_order(item_code=item, warehouse="Stores - _TC")
		group = frappe.db.get_value("Warehouse", "Stores - _TC", "parent_warehouse")

		report_data = item_shortage_report({"company": so.company, "warehouse": [group]})[1]

		self.assertIn(item, [row.get("item_code") for row in report_data])

	def test_quantity_columns_add_up_to_the_projected_qty(self):
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request

		item = make_item(properties={"is_stock_item": 1}).name
		so = make_sales_order(item_code=item, warehouse="Stores - _TC", qty=12)
		make_material_request(item_code=item, warehouse="Stores - _TC", qty=4)

		row = next(
			row for row in item_shortage_report({"company": so.company})[1] if row.get("item_code") == item
		)

		self.assertEqual(
			(row.get("indented_qty"), row.get("reserved_qty"), row.get("projected_qty")), (4, 12, -8)
		)
