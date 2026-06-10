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


def quality_control_lots_for(stock_entry_name):
	return frappe.get_all(
		"Quality Control Lot",
		filters={"source_document_type": "Stock Entry", "source_document": stock_entry_name},
		fields=["item_code", "received_qty", "quality_warehouse", "status"],
	)


class TestQualityQuarantine(ERPNextTestSuite):
	def test_quality_control_lot_minted_on_receipt_into_qc_warehouse(self):
		qc = make_qc_warehouse()
		item = make_item(properties={"is_stock_item": 1}).name
		se = make_stock_entry(item_code=item, qty=7, to_warehouse=qc, purpose="Material Receipt", rate=100)

		lots = quality_control_lots_for(se.name)
		self.assertEqual(len(lots), 1)
		self.assertEqual(lots[0].received_qty, 7)
		self.assertEqual(lots[0].quality_warehouse, qc)
		self.assertEqual(lots[0].status, "Under Inspection")

	def test_no_quality_control_lot_for_normal_warehouse(self):
		item = make_item(properties={"is_stock_item": 1}).name
		se = make_stock_entry(
			item_code=item, qty=5, to_warehouse=REAL_WH, purpose="Material Receipt", rate=100
		)
		self.assertEqual(quality_control_lots_for(se.name), [])

	def _quarantine_item(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
			),
		)
		item.save()
		return item.name

	def test_quarantine_routes_to_quality_warehouse_and_mints_lot(self):
		qc = make_qc_warehouse()
		store = make_warehouse("_Test QC Routed Store", quality_warehouse=qc)
		item = self._quarantine_item()

		se = make_stock_entry(item_code=item, qty=4, to_warehouse=store, purpose="Material Receipt", rate=100)

		# the receipt was redirected into the Quality Control warehouse on validate…
		self.assertEqual(se.items[0].t_warehouse, qc)
		# …the document still submitted freely, and the lot was minted there
		lots = quality_control_lots_for(se.name)
		self.assertEqual(len(lots), 1)
		self.assertEqual(lots[0].quality_warehouse, qc)
		self.assertEqual(lots[0].received_qty, 4)

	def test_quality_warehouse_exit_is_locked(self):
		qc = make_qc_warehouse()
		item = make_item(properties={"is_stock_item": 1}).name
		make_stock_entry(item_code=item, qty=5, to_warehouse=qc, purpose="Material Receipt", rate=100)

		# an ordinary transfer out of the Quality Control warehouse is blocked…
		self.assertRaises(
			frappe.ValidationError,
			make_stock_entry,
			item_code=item,
			qty=2,
			from_warehouse=qc,
			to_warehouse=REAL_WH,
			purpose="Material Transfer",
		)

		# …while a Quality Control Release takes it out cleanly
		make_stock_entry(
			item_code=item, qty=2, from_warehouse=qc, to_warehouse=REAL_WH, purpose="Quality Control Release"
		)

	def test_cancellation_reversal_is_exempt_from_the_lock(self):
		qc = make_qc_warehouse()
		item = make_item(properties={"is_stock_item": 1}).name
		se = make_stock_entry(item_code=item, qty=3, to_warehouse=qc, purpose="Material Receipt", rate=100)
		se.cancel()  # reversal takes stock back out of the Quality Control warehouse — allowed

	def test_stock_reconciliation_blocked_on_quality_warehouse(self):
		qc = make_qc_warehouse()
		item = make_item(properties={"is_stock_item": 1}).name

		reconciliation = frappe.new_doc("Stock Reconciliation")
		reconciliation.company = "_Test Company"
		reconciliation.purpose = "Stock Reconciliation"
		reconciliation.append("items", {"item_code": item, "warehouse": qc, "qty": 10, "valuation_rate": 100})
		self.assertRaises(frappe.ValidationError, reconciliation.save)

	def test_quarantine_requires_configured_quality_warehouse(self):
		store = make_warehouse("_Test QC Unconfigured Store")  # no quality_warehouse
		item = self._quarantine_item()

		self.assertRaises(
			frappe.ValidationError,
			make_stock_entry,
			item_code=item,
			qty=1,
			to_warehouse=store,
			purpose="Material Receipt",
			rate=100,
		)
