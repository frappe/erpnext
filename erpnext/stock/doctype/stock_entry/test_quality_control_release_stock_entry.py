# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

SOURCE_WH = "_Test Warehouse - _TC"
TARGET_WH = "_Test Quality Control Release Target - _TC"


def ensure_warehouse(name=TARGET_WH):
	if not frappe.db.exists("Warehouse", name):
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "_Test Quality Control Release Target",
				"company": "_Test Company",
			}
		).insert(ignore_permissions=True)
	return name


def get_qty(item_code, warehouse):
	return frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty") or 0.0


class TestQualityControlReleaseStockEntry(ERPNextTestSuite):
	def test_quality_control_release_moves_stock_like_a_transfer(self):
		ensure_warehouse()
		item = make_item(properties={"is_stock_item": 1}).name

		# seed stock in the source warehouse
		make_stock_entry(item_code=item, qty=10, to_warehouse=SOURCE_WH, purpose="Material Receipt", rate=100)

		src_before = get_qty(item, SOURCE_WH)
		tgt_before = get_qty(item, TARGET_WH)

		se = make_stock_entry(
			item_code=item,
			qty=6,
			from_warehouse=SOURCE_WH,
			to_warehouse=TARGET_WH,
			purpose="Quality Control Release",
		)

		# behaves like a transfer: distinct purpose, resolves to the standard type,
		# and stock moves source -> target with no quantity lost
		self.assertEqual(se.purpose, "Quality Control Release")
		self.assertEqual(se.stock_entry_type, "Quality Control Release")
		self.assertEqual(get_qty(item, SOURCE_WH), src_before - 6)
		self.assertEqual(get_qty(item, TARGET_WH), tgt_before + 6)
