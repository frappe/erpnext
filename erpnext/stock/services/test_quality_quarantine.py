# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.services.test_quality_warehouse import ensure_quality_warehouse_type, make_warehouse
from erpnext.tests.utils import ERPNextTestSuite

REAL_WH = "_Test Warehouse - _TC"


def make_qc_warehouse(name="_Test QC Mint WH"):
	ensure_quality_warehouse_type()
	return make_warehouse(name, warehouse_type="Quality")


def quality_control_lots_for(stock_entry_name):
	return frappe.get_all(
		"Quality Control Lot",
		filters={"source_document_type": "Stock Entry", "source_document": stock_entry_name},
		fields=["name", "item_code", "received_qty", "quality_warehouse", "status"],
	)


def submit_inspection_for_lot(lot_name, status="Accepted", reading_bundle=None):
	lot = frappe.get_doc("Quality Control Lot", lot_name)
	inspection = frappe.get_doc(
		{
			"doctype": "Quality Inspection",
			"inspection_type": "Incoming",
			"reference_type": "Quality Control Lot",
			"reference_name": lot.name,
			"item_code": lot.item_code,
			"sample_size": 1,
			"report_date": nowdate(),
			"inspected_by": frappe.session.user,
			"manual_inspection": 1,
			"status": status,
			"reading_bundle": reading_bundle,
		}
	)
	inspection.insert(ignore_permissions=True)
	inspection.submit()
	return inspection


def make_release(lot_name, qty, to_warehouse):
	lot = frappe.get_doc("Quality Control Lot", lot_name)
	release = frappe.new_doc("Stock Entry")
	release.purpose = "Quality Control Release"
	release.stock_entry_type = "Quality Control Release"
	release.company = "_Test Company"
	release.quality_control_lot = lot.name
	release.append(
		"items",
		{
			"item_code": lot.item_code,
			"qty": qty,
			"s_warehouse": lot.quality_warehouse,
			"t_warehouse": to_warehouse,
		},
	)
	release.insert()
	release.submit()
	return release


def get_qty(item_code, warehouse):
	return frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty") or 0.0


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
		# dedicated Quality Control warehouse no store points at, so nothing auto-releases
		qc = make_qc_warehouse("_Test QC Lock WH")
		item = make_item(properties={"is_stock_item": 1}).name
		se = make_stock_entry(item_code=item, qty=5, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

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

		# …a release without a lot reference is blocked too…
		self.assertRaises(
			frappe.ValidationError,
			make_stock_entry,
			item_code=item,
			qty=2,
			from_warehouse=qc,
			to_warehouse=REAL_WH,
			purpose="Quality Control Release",
		)

		# …and a release backed by the lot only works once its inspection is submitted
		self.assertRaises(frappe.ValidationError, make_release, lot, 2, REAL_WH)
		submit_inspection_for_lot(lot)
		make_release(lot, 2, REAL_WH)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Partially Released")

	def test_cancellation_reversal_is_exempt_from_the_lock(self):
		qc = make_qc_warehouse()
		item = make_item(properties={"is_stock_item": 1}).name
		se = make_stock_entry(item_code=item, qty=3, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		se.cancel()  # reversal takes stock back out of the Quality Control warehouse — allowed
		# the untouched lot is removed along with the reversed stock
		self.assertFalse(frappe.db.exists("Quality Control Lot", lot))

	def test_inspection_acceptance_releases_quarantined_stock(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		qc = make_qc_warehouse("_Test QC Auto WH")
		store = make_warehouse("_Test QC Auto Store", quality_warehouse=qc)

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry", warehouse_role="Inbound", quality_control_mode="Quarantine"
			),
		)
		item.save()

		receipt = make_stock_entry(
			item_code=item.name, qty=6, to_warehouse=store, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(receipt.name)[0].name
		self.assertEqual(get_qty(item.name, store), 0)  # quarantined, not in the store

		# acceptance auto-creates the release: stock lands in the store, lot closes
		submit_inspection_for_lot(lot, status="Accepted")
		self.assertEqual(get_qty(item.name, store), 6)
		self.assertEqual(get_qty(item.name, qc), 0)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Released")

		# the source receipt can no longer be cancelled while the release stands
		self.assertRaises(frappe.ValidationError, receipt.cancel)

	def test_per_unit_inspection_splits_the_lot(self):
		from erpnext.stock.doctype.quality_inspection_reading_bundle.test_quality_inspection_reading_bundle import (
			make_bundle,
		)

		qc = make_qc_warehouse("_Test QC Split WH")
		store = make_warehouse("_Test QC Split Store", quality_warehouse=qc)
		item = make_item(properties={"is_stock_item": 1}).name
		se = make_stock_entry(item_code=item, qty=5, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		# 5 units inspected individually: 3 pass, 2 fail
		bundle = make_bundle(
			5,
			{
				1: ["Accepted"],
				2: ["Accepted"],
				3: ["Rejected"],
				4: ["Accepted"],
				5: ["Rejected"],
			},
		)
		submit_inspection_for_lot(lot, status="Accepted", reading_bundle=bundle.name)

		# accepted units released to the store, rejected units stay quarantined
		self.assertEqual(get_qty(item, store), 3)
		self.assertEqual(get_qty(item, qc), 2)
		lot_doc = frappe.get_doc("Quality Control Lot", lot)
		self.assertEqual(lot_doc.accepted_qty, 3)
		self.assertEqual(lot_doc.rejected_qty, 2)
		self.assertEqual(lot_doc.pending_qty, 0)

	def test_inspection_rejection_keeps_stock_quarantined(self):
		qc = make_qc_warehouse("_Test QC Reject WH")
		item = make_item(properties={"is_stock_item": 1}).name
		se = make_stock_entry(item_code=item, qty=4, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		submit_inspection_for_lot(lot, status="Rejected")

		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Rejected")
		self.assertEqual(get_qty(item, qc), 4)  # stays under quality hold for the purchase return

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
