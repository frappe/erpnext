# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.services.quality_retest import process_periodic_retests
from erpnext.stock.services.test_quality_quarantine import (
	get_qty,
	make_qc_warehouse,
	submit_inspection_for_lot,
)
from erpnext.stock.services.test_quality_warehouse import make_warehouse
from erpnext.tests.utils import ERPNextTestSuite

INTERVAL = 30


def make_retest_item(series):
	item = make_item(
		properties={
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": series,
		}
	)
	item.append(
		"quality_triggers",
		trigger_row(
			trigger_type="Periodic Re-test",
			document_type=None,
			warehouse_role=None,
			quality_control_mode=None,
			retest_interval_days=INTERVAL,
		),
	)
	item.save()
	return item.name


class TestQualityRetest(ERPNextTestSuite):
	def test_retest_date_is_initialised_for_new_batches(self):
		qc = make_qc_warehouse("_Test QC Retest Init WH")
		store = make_warehouse("_Test QC Retest Init Store", quality_warehouse=qc)
		item = make_retest_item("TQRI-.####")

		make_stock_entry(item_code=item, qty=3, to_warehouse=store, purpose="Material Receipt", rate=100)
		batch = frappe.get_all("Batch", filters={"item": item}, pluck="name")[0]

		process_periodic_retests()

		next_date = frappe.db.get_value("Batch", batch, "next_quality_inspection_date")
		self.assertIsNotNone(next_date)
		self.assertGreater(getdate(next_date), getdate(today()))
		# not due: nothing was quarantined
		self.assertEqual(get_qty(item, store), 3)

	def test_due_batch_is_quarantined_and_decision_schedules_next_retest(self):
		qc = make_qc_warehouse("_Test QC Retest WH")
		store = make_warehouse("_Test QC Retest Store", quality_warehouse=qc)
		item = make_retest_item("TQRD-.####")

		make_stock_entry(item_code=item, qty=5, to_warehouse=store, purpose="Material Receipt", rate=100)
		batch = frappe.get_all("Batch", filters={"item": item}, pluck="name")[0]
		frappe.db.set_value("Batch", batch, "next_quality_inspection_date", add_days(today(), -1))

		process_periodic_retests()

		# the due batch moved into the Quality Control warehouse and a lot was minted
		self.assertEqual(get_qty(item, store), 0)
		self.assertEqual(get_qty(item, qc), 5)
		lot = frappe.db.get_value(
			"Quality Control Lot",
			{"item_code": item, "quality_warehouse": qc, "status": "Under Inspection"},
			"name",
		)
		self.assertIsNotNone(lot)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "batch_no"), batch)
		# the date is cleared while the batch is under inspection
		self.assertIsNone(frappe.db.get_value("Batch", batch, "next_quality_inspection_date"))

		# acceptance releases the stock back and schedules the next re-test
		submit_inspection_for_lot(lot, status="Accepted")
		self.assertEqual(get_qty(item, store), 5)
		self.assertEqual(
			getdate(frappe.db.get_value("Batch", batch, "next_quality_inspection_date")),
			getdate(add_days(today(), INTERVAL)),
		)
