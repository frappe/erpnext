# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.itemwise_recommended_reorder_level.itemwise_recommended_reorder_level import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "Stores - _TC"


class TestItemwiseRecommendedReorderLevel(ERPNextTestSuite):
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

	def test_purchase_returns_are_not_consumption(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_return
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item = make_item(properties={"is_stock_item": 1}).name
		receipt = make_purchase_receipt(item_code=item, qty=10, rate=10, posting_date="2026-06-02")
		purchase_return = make_purchase_return(receipt.name)
		purchase_return.items[0].qty = -2
		purchase_return.posting_date = "2026-06-03"
		purchase_return.set_posting_time = 1
		purchase_return.submit()

		row = self.find_row(self.run_report(), item)

		self.assertEqual(flt(row[7]), 0)

	def consumed_today(self, item_code):
		from frappe.utils import today

		row = self.find_row(self.run_report(from_date=today(), to_date=today()), item_code)
		return flt(row[7]) if row else 0

	def test_subcontracting_receipt_consumption_counts_but_its_return_does_not(self):
		import copy

		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.controllers.tests.test_subcontracting_controller import (
			get_rm_items,
			get_subcontracting_order,
			make_bom_for_subcontracted_items,
			make_raw_materials,
			make_service_items,
			make_stock_in_entry,
			make_stock_transfer_entry,
			make_subcontracted_items,
		)
		from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
			make_subcontracting_receipt,
		)

		make_subcontracted_items()
		make_raw_materials()
		make_service_items()
		make_bom_for_subcontracted_items()
		sco = get_subcontracting_order()
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name, rm_items=rm_items, itemwise_details=copy.deepcopy(itemwise_details)
		)
		receipt = make_subcontracting_receipt(sco.name)
		receipt.save()
		raw_material = receipt.supplied_items[0].rm_item_code
		finished_good = receipt.items[0].item_code
		before = {item: self.consumed_today(item) for item in (raw_material, finished_good)}

		receipt.submit()
		make_return_doc("Subcontracting Receipt", receipt.name).submit()

		expected_rm = sum(
			row.consumed_qty for row in receipt.supplied_items if row.rm_item_code == raw_material
		)
		self.assertEqual(self.consumed_today(raw_material) - before[raw_material], expected_rm)
		self.assertEqual(self.consumed_today(finished_good), before[finished_good])

	def test_from_date_after_to_date_is_refused_with_the_right_message(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			"From Date cannot be after To Date",
			self.run_report,
			from_date="2026-06-10",
			to_date="2026-06-01",
		)
