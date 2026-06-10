# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.quality_control_lot_reconciliation.quality_control_lot_reconciliation import (
	execute,
)
from erpnext.stock.services.test_quality_quarantine import (
	make_qc_warehouse,
	make_quarantine_item,
	quality_control_lots_for,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestQualityControlLotReconciliation(ERPNextTestSuite):
	def test_balanced_quarantine_reconciles_and_tampering_is_flagged(self):
		qc = make_qc_warehouse("_Test QC Recon WH")
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=8, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		def row():
			_columns, data = execute({"warehouse": qc})
			matches = [d for d in data if d["item_code"] == item]
			return matches[0] if matches else None

		# controlled flows keep the ledger and the lots in lockstep
		balanced = row()
		self.assertEqual(balanced["ledger_qty"], 8)
		self.assertEqual(balanced["pending_qty"], 8)
		self.assertEqual(balanced["difference"], 0)

		# drift that bypasses the application layer is surfaced
		frappe.db.set_value("Quality Control Lot", lot, "pending_qty", 5, update_modified=False)
		tampered = row()
		self.assertEqual(tampered["difference"], 3)
