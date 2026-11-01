# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest import TestCase
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.controllers.stock_controller import get_sl_entries_for_preview, show_accounting_ledger_preview
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


class TestLedgerPreview(TestCase):
	def test_in_out_rate_is_only_set_for_outgoing_entries(self):
		stock_ledger_entries = [
			frappe._dict(actual_qty=5, stock_value_difference=10),
			frappe._dict(actual_qty=-5, stock_value_difference=-15),
		]

		with patch("frappe.get_all", return_value=stock_ledger_entries):
			entries = get_sl_entries_for_preview("Delivery Note", "DN-0001", [])

		self.assertIsNone(entries[0].get("in_out_rate"))
		self.assertEqual(entries[1].in_out_rate, 3)


class TestLedgerPreviewPermissions(FrappeTestCase):
	def test_accounting_ledger_preview_needs_gl_entry_read(self):
		stock_entry = make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=1, basic_rate=100, do_not_submit=True
		)
		user = frappe.get_doc(
			{"doctype": "User", "email": "ledger-preview@example.com", "first_name": "Preview"}
		).insert(ignore_permissions=True)
		user.add_roles("Stock User")

		with self.set_user(user.name), self.assertRaises(frappe.PermissionError):
			show_accounting_ledger_preview(stock_entry.company, stock_entry.doctype, stock_entry.name)
