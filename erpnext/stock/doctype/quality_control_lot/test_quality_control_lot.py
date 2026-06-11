# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.services.test_quality_warehouse import ensure_quality_warehouse_type, make_warehouse
from erpnext.tests.utils import ERPNextTestSuite


def qc_warehouse():
	ensure_quality_warehouse_type()
	return make_warehouse("_Test Quality Control Lot WH", warehouse_type="Quality")


def make_quality_control_lot(received_qty=10, accepted_qty=0, rejected_qty=0, decided_qty=None):
	if decided_qty is None:
		# released or rejected stock implies a verdict that decided it
		decided_qty = accepted_qty + rejected_qty
	return frappe.get_doc(
		{
			"doctype": "Quality Control Lot",
			"item_code": make_item(properties={"is_stock_item": 1}).name,
			"company": "_Test Company",
			"quality_warehouse": qc_warehouse(),
			"received_qty": received_qty,
			"decided_qty": decided_qty,
			"accepted_qty": accepted_qty,
			"rejected_qty": rejected_qty,
		}
	).insert(ignore_permissions=True)


class TestQualityControlLot(ERPNextTestSuite):
	def test_status_under_inspection(self):
		lot = make_quality_control_lot()
		self.assertEqual(lot.status, "Under Inspection")
		self.assertEqual(lot.pending_qty, 10)

	def test_status_partially_released(self):
		lot = make_quality_control_lot(accepted_qty=4)
		self.assertEqual(lot.status, "Partially Released")
		self.assertEqual(lot.pending_qty, 6)

	def test_status_under_inspection_while_partly_decided_and_unmoved(self):
		# a rejection is a verdict, not a movement: with units undecided and
		# nothing released, the lot is still under inspection
		lot = make_quality_control_lot(rejected_qty=1, decided_qty=2)
		self.assertEqual(lot.status, "Under Inspection")

	def test_status_awaiting_release_when_decided_but_unmoved(self):
		lot = make_quality_control_lot(decided_qty=10)
		self.assertEqual(lot.status, "Awaiting Release")
		self.assertEqual(lot.pending_qty, 10)

	def test_status_released_when_fully_resolved(self):
		lot = make_quality_control_lot(accepted_qty=8, rejected_qty=2)
		self.assertEqual(lot.status, "Released")
		self.assertEqual(lot.pending_qty, 0)

	def test_status_rejected_when_all_rejected(self):
		lot = make_quality_control_lot(rejected_qty=10)
		self.assertEqual(lot.status, "Rejected")
		self.assertEqual(lot.pending_qty, 0)
