# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.itemwise_recommended_reorder_level.itemwise_recommended_reorder_level import (
	execute,
)

WAREHOUSE = "Stores - _TC"


class TestItemwiseRecommendedReorderLevel(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def run_report(self, **extra):
		filters = frappe._dict({"from_date": "2026-06-01", "to_date": "2026-06-10"})
		filters.update(extra)
		return execute(filters)[1]

	def find_row(self, data, item_code):
		for row in data:
			if row[0] == item_code:
				return row
		return None

	def test_bundle_deliveries_count_for_their_components(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.packed_item.test_packed_item import create_product_bundle

		bundle, components = create_product_bundle([1])
		make_stock_entry(
			item_code=components[0], to_warehouse=WAREHOUSE, qty=10, rate=100, posting_date="2026-06-01"
		)
		create_delivery_note(item_code=bundle, qty=5, warehouse=WAREHOUSE, posting_date="2026-06-05")

		row = self.find_row(self.run_report(), components[0])

		self.assertEqual(flt(row[8]), 5)
