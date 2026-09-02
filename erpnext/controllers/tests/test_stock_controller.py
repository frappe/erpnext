# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.controllers.stock_controller import (
	show_accounting_ledger_preview,
	show_stock_ledger_preview,
)
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestLedgerPreviewPermission(ERPNextTestSuite):
	def test_accounting_ledger_preview_requires_read_permission(self):
		company = "_Test Company"
		je = make_journal_entry("_Test Cash - _TC", "_Test Bank - _TC", 100, submit=True)

		email = "ledger_preview_no_role@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "No Role",
					"user_type": "Website User",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		try:
			frappe.set_user(email)
			self.assertRaises(
				frappe.PermissionError,
				show_accounting_ledger_preview,
				company,
				"Journal Entry",
				je.name,
			)
		finally:
			frappe.set_user("Administrator")

		# a permitted user is still able to read the preview
		accounting_ledger_result = show_accounting_ledger_preview(company, "Journal Entry", je.name)
		self.assertTrue(accounting_ledger_result.get("gl_data"))

	def test_stock_ledger_preview_requires_read_permission(self):
		company = "_Test Company"
		pr = make_purchase_receipt()

		email = "ledger_preview_no_role@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "No Role",
					"user_type": "Website User",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		try:
			frappe.set_user(email)
			self.assertRaises(
				frappe.PermissionError,
				show_stock_ledger_preview,
				company,
				"Purchase Receipt",
				pr.name,
			)
		finally:
			frappe.set_user("Administrator")

		stock_ledger_result = show_stock_ledger_preview(company, "Purchase Receipt", pr.name)
		self.assertTrue(stock_ledger_result.get("sl_data"))


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
		# A later SLE for the same item+warehouse must be reported as a future entry, which
		# exercises the GROUP BY query in future_sle_exists on both engines.
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

	def _make_opening_entry(self, item, warehouse):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		opening = make_stock_entry(
			item_code=item,
			target=warehouse,
			qty=100,
			basic_rate=100,
			posting_date=add_days(today(), -5),
			posting_time="01:00:00",
		)
		self.addCleanup(self._cancel_and_delete, "Stock Entry", opening.name)

		return opening

	def _later_sle(self, item, warehouse, opening):
		sle = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"item_code": item,
				"warehouse": warehouse,
				"posting_date": today(),
				"posting_time": "12:00:00",
				"voucher_type": "Stock Entry",
				"voucher_no": opening.name,
				"actual_qty": 7,
				"incoming_rate": 100,
				"qty_after_transaction": 107,
				"valuation_rate": 100,
				"stock_value": 10700,
				"company": opening.company,
				"stock_uom": "Nos",
			}
		)
		sle.flags.ignore_permissions = True
		sle.flags.ignore_links = True

		return sle

	def _submit_entry(self, item, warehouse, inject=None):
		from erpnext.stock import stock_ledger
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		original_make_entry = stock_ledger.make_entry
		injected = []

		def make_entry_with_injection(*args, **kwargs):
			if inject is not None and not injected:
				injected.append(True)
				inject.submit()
			return original_make_entry(*args, **kwargs)

		stock_ledger.make_entry = make_entry_with_injection
		try:
			entry = make_stock_entry(
				item_code=item,
				target=warehouse,
				qty=5,
				basic_rate=500,
				posting_date=today(),
				posting_time="06:00:00",
			)
		finally:
			stock_ledger.make_entry = original_make_entry

		self.addCleanup(self._cancel_and_delete, "Stock Entry", entry.name)
		if inject is not None:
			self.assertTrue(injected, "the later SL Entry was not written during the submit")

		return entry

	def _reposts_queued_for(self, item, warehouse, voucher_no):
		names = set(
			frappe.get_all(
				"Repost Item Valuation",
				filters={"docstatus": 1, "item_code": item, "warehouse": warehouse},
				pluck="name",
			)
		) | set(
			frappe.get_all(
				"Repost Item Valuation",
				filters={"docstatus": 1, "voucher_no": voucher_no},
				pluck="name",
			)
		)
		for name in names:
			self.addCleanup(frappe.delete_doc, "Repost Item Valuation", name, force=1)

		return names

	def test_repost_queued_for_entry_backdated_while_its_sl_entries_were_written(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item("_Test Concurrent Backdated Item", {"is_stock_item": 1}).name
		warehouse = "_Test Warehouse - _TC"

		opening = self._make_opening_entry(item, warehouse)
		backdated = self._submit_entry(item, warehouse, inject=self._later_sle(item, warehouse, opening))

		self.assertTrue(
			self._reposts_queued_for(item, warehouse, backdated.name),
			"No Repost Item Valuation was queued for an entry that a later SL Entry made backdated",
		)

	def test_repost_queued_against_voucher_when_item_based_reposting_is_off(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item("_Test Voucher Based Repost Item", {"is_stock_item": 1}).name
		warehouse = "_Test Warehouse - _TC"

		with self.change_settings("Stock Reposting Settings", item_based_reposting=0):
			opening = self._make_opening_entry(item, warehouse)
			backdated = self._submit_entry(item, warehouse, inject=self._later_sle(item, warehouse, opening))

			self.assertTrue(
				frappe.get_all(
					"Repost Item Valuation",
					filters={"docstatus": 1, "voucher_no": backdated.name},
					pluck="name",
				),
				"No voucher based Repost Item Valuation was queued",
			)

	def test_no_repost_queued_when_nothing_was_written_after_the_entry(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item("_Test Unconcurrent Item", {"is_stock_item": 1}).name
		warehouse = "_Test Warehouse - _TC"

		self._make_opening_entry(item, warehouse)
		entry = self._submit_entry(item, warehouse)

		self.assertFalse(
			self._reposts_queued_for(item, warehouse, entry.name),
			"A Repost Item Valuation was queued for an entry with nothing posted after it",
		)
