# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.tests.utils import ERPNextTestSuite


class TestStockControllerConversions(ERPNextTestSuite):
	@staticmethod
	def _cancel_and_delete(doctype, name):
		if not frappe.db.exists(doctype, name):
			return
		doc = frappe.get_doc(doctype, name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc(doctype, name, force=1)

	def test_future_sle_exists_detects_later_entries(self):
		# future_sle_exists / get_conditions_to_validate_future_sle were converted to query builder
		# (Count + Criterion.any). A later SLE for the same item+warehouse must be detected, which
		# exercises the converted GROUP BY query on both engines.
		from erpnext.controllers.stock_controller import future_sle_exists
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item("_Test Future SLE Item", {"is_stock_item": 1}).name
		se = make_stock_entry(item_code=item, target="_Test Warehouse - _TC", qty=10, basic_rate=100)
		self.addCleanup(self._cancel_and_delete, "Stock Entry", se.name)

		# Pretend a different voucher posts a day earlier for the same item/warehouse: the existing
		# (later) SLE must be reported as a future entry.
		args = frappe._dict(
			voucher_type="Stock Entry",
			voucher_no="_TEST-NONEXISTENT-SE",
			posting_date=add_days(today(), -1),
			posting_time="00:00:00",
		)
		sl_entries = [frappe._dict(item_code=item, warehouse="_Test Warehouse - _TC")]

		self.assertTrue(future_sle_exists(args, sl_entries))
