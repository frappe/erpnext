# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_projected_qty.stock_projected_qty import execute

WAREHOUSE = "Stores - _TC"


class TestStockProjectedQty(FrappeTestCase):
	def run_report(self, item_code):
		filters = frappe._dict(company="_Test Company", item_code=item_code)
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
