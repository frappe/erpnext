# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.services.test_quality_warehouse import ensure_quality_warehouse_type, make_warehouse
from erpnext.tests.utils import ERPNextTestSuite

REAL_WH = "_Test Warehouse - _TC"


def make_qc_warehouse():
	ensure_quality_warehouse_type()
	return make_warehouse("_Test QC Mint WH", warehouse_type="Quality")


def qc_lots_for(stock_entry_name):
	return frappe.get_all(
		"QC Lot",
		filters={"source_document_type": "Stock Entry", "source_document": stock_entry_name},
		fields=["item_code", "received_qty", "quality_warehouse", "status"],
	)


class TestQualityQuarantine(ERPNextTestSuite):
	def test_qc_lot_minted_on_receipt_into_qc_warehouse(self):
		qc = make_qc_warehouse()
		item = make_item(properties={"is_stock_item": 1}).name
		se = make_stock_entry(item_code=item, qty=7, to_warehouse=qc, purpose="Material Receipt", rate=100)

		lots = qc_lots_for(se.name)
		self.assertEqual(len(lots), 1)
		self.assertEqual(lots[0].received_qty, 7)
		self.assertEqual(lots[0].quality_warehouse, qc)
		self.assertEqual(lots[0].status, "Under Inspection")

	def test_no_qc_lot_for_normal_warehouse(self):
		item = make_item(properties={"is_stock_item": 1}).name
		se = make_stock_entry(
			item_code=item, qty=5, to_warehouse=REAL_WH, purpose="Material Receipt", rate=100
		)
		self.assertEqual(qc_lots_for(se.name), [])
