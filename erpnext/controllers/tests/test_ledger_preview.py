# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.controllers.ledger_preview import get_sl_entries_for_preview
from erpnext.tests.utils import ERPNextTestSuite


class TestLedgerPreview(ERPNextTestSuite):
	def test_in_out_rate_is_only_set_for_outgoing_entries(self):
		stock_ledger_entries = [
			frappe._dict(actual_qty=5, stock_value_difference=10),
			frappe._dict(actual_qty=-5, stock_value_difference=-15),
		]

		with patch("frappe.get_all", return_value=stock_ledger_entries):
			entries = get_sl_entries_for_preview("Delivery Note", "DN-0001", [])

		self.assertIsNone(entries[0].get("in_out_rate"))
		self.assertEqual(entries[1].in_out_rate, 3)
