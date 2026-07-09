# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from erpnext.tests.utils import ERPNextTestSuite


class TestProductionPlanningReport(ERPNextTestSuite):
	def test_report_runs_and_sums_on_order_qty(self):
		# get_purchase_details groups Purchase Order Item by (item_code, warehouse) while summing qty;
		# this exercises that GROUP BY on both engines (loose on MariaDB, must be aggregated on Postgres).
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
		from erpnext.manufacturing.report.production_planning_report.production_planning_report import execute

		wh = "_Test Warehouse - _TC"
		wo = make_wo_order_test_record(production_item="_Test FG Item", qty=2, source_warehouse=wh)
		self.addCleanup(self._cancel_and_delete, "Work Order", wo.name)

		rm = wo.required_items[0].item_code
		for qty in (3, 4):
			po = create_purchase_order(item_code=rm, warehouse=wh, qty=qty, rate=10)
			self.addCleanup(self._cancel_and_delete, "Purchase Order", po.name)

		filters = {
			"company": "_Test Company",
			"based_on": "Work Order",
			"docnames": [wo.name],
			"raw_material_warehouse": wh,
		}
		columns, data = execute(filters)

		self.assertTrue(columns)
		rm_rows = [d for d in data if d.get("item_code") == rm and d.get("arrival_qty")]
		self.assertTrue(rm_rows)
		# both on-order PO lines (3 + 4) are summed, not arbitrary-picked
		self.assertEqual(rm_rows[0]["arrival_qty"], 7)

	@staticmethod
	def _cancel_and_delete(doctype, name):
		import frappe

		if not frappe.db.exists(doctype, name):
			return
		doc = frappe.get_doc(doctype, name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc(doctype, name, force=1)
