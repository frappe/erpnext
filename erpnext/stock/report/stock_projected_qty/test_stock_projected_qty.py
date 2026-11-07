# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_projected_qty.stock_projected_qty import execute

WAREHOUSE = "Stores - _TC"


class TestStockProjectedQty(FrappeTestCase):
	def run_report(self, item_code, warehouse=None):
		filters = frappe._dict(company="_Test Company", item_code=item_code)
		if warehouse:
			filters.warehouse = warehouse
		columns, data = execute(filters)
		fields = [column["fieldname"] for column in columns]
		return [dict(zip(fields, row, strict=False)) for row in data]

	def test_company_filter_excludes_other_company_warehouses(self):
		item = "_Test Item"
		make_stock_entry(item_code=item, qty=5, to_warehouse=WAREHOUSE, basic_rate=100)
		make_stock_entry(
			item_code=item,
			qty=7,
			to_warehouse="Stores - _TC1",
			company="_Test Company 1",
			basic_rate=100,
		)

		warehouses = {row["warehouse"] for row in self.run_report(item)}
		self.assertIn(WAREHOUSE, warehouses)
		self.assertNotIn("Stores - _TC1", warehouses)

	def test_shortage_qty_takes_off_pos_reserved_qty(self):
		from unittest.mock import patch

		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(
			properties={
				"is_stock_item": 1,
				"reorder_levels": [
					{
						"warehouse": WAREHOUSE,
						"warehouse_reorder_level": 10,
						"warehouse_reorder_qty": 20,
						"material_request_type": "Purchase",
					}
				],
			}
		).name
		make_stock_entry(item_code=item, qty=12, to_warehouse=WAREHOUSE, basic_rate=100)

		with patch(
			"erpnext.stock.report.stock_projected_qty.stock_projected_qty.get_pos_reserved_qty",
			return_value=5,
		):
			row = self.run_report(item, warehouse=WAREHOUSE)[0]

		self.assertEqual((row["projected_qty"], row["shortage_qty"]), (7, 3))

	def test_include_uom_leaves_items_without_that_uom_blank(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 1, "stock_uom": "Nos"}).name
		make_stock_entry(item_code=item, qty=24, to_warehouse=WAREHOUSE, basic_rate=100)

		columns, data = execute(frappe._dict(company="_Test Company", item_code=item, include_uom="Box"))
		row = dict(zip([column["fieldname"] for column in columns], data[0], strict=False))

		self.assertEqual((row["actual_qty"], row["actual_qty_box"]), (24, None))
