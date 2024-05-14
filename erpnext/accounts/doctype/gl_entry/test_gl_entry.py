# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe
from frappe.model.naming import parse_naming_series

from erpnext.accounts.doctype.gl_entry.gl_entry import rename_gle_sle_docs
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry


class TestGLEntry(unittest.TestCase):
	def test_round_off_entry(self):
		frappe.db.set_value("Company", "_Test Company", "round_off_account", "_Test Write Off - _TC")
		frappe.db.set_value("Company", "_Test Company", "round_off_cost_center", "_Test Cost Center - _TC")

		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			100,
			"_Test Cost Center - _TC",
			submit=False,
		)

		jv.get("accounts")[0].debit = 100.01
		jv.flags.ignore_validate = True
		jv.submit()

		round_off_entry = frappe.db.sql(
			"""select name from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_no = %s
			and account='_Test Write Off - _TC' and cost_center='_Test Cost Center - _TC'
			and debit = 0 and credit = '.01'""",
			jv.name,
		)

		self.assertTrue(round_off_entry)

	def test_rename_entries(self):
		# enable deferring in config to test deferring
		frappe.db.set_single_value("Accounts Settings","deferred_naming_for_stock_ledger_entry_and_gl_entry",1)
		je = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC", "_Test Bank - _TC", 100, submit=True
		)
		rename_gle_sle_docs()
		naming_series = parse_naming_series(parts=frappe.get_meta("GL Entry").autoname.split(".")[:-1])

		je = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC", "_Test Bank - _TC", 100, submit=True
		)

		gl_entries = frappe.get_all(
			"GL Entry",
			fields=["name", "to_rename"],
			filters={"voucher_type": "Journal Entry", "voucher_no": je.name},
			order_by="creation",
		)

		self.assertTrue(all(entry.to_rename == 1 for entry in gl_entries))
		old_naming_series_current_value = frappe.db.sql(
			"SELECT current from tabSeries where name = %s", naming_series
		)[0][0]

		rename_gle_sle_docs()

		new_gl_entries = frappe.get_all(
			"GL Entry",
			fields=["name", "to_rename"],
			filters={"voucher_type": "Journal Entry", "voucher_no": je.name},
			order_by="creation",
		)
		self.assertTrue(all(entry.to_rename == 0 for entry in new_gl_entries))

		self.assertTrue(
			all(new.name != old.name for new, old in zip(gl_entries, new_gl_entries, strict=False))
		)

		new_naming_series_current_value = frappe.db.sql(
			"SELECT current from tabSeries where name = %s", naming_series
		)[0][0]
		self.assertEqual(old_naming_series_current_value + 2, new_naming_series_current_value)
		# disable deferring to test skipping of setting up name changing
		frappe.db.set_single_value("Accounts Settings","deferred_naming_for_stock_ledger_entry_and_gl_entry",0)
		old_naming_series_current_value = frappe.db.sql(
			"SELECT current from tabSeries where name = %s", naming_series
		)[0][0]
		je = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC", "_Test Bank - _TC", 100, submit=True
		)
		gl_entries = frappe.get_all(
			"GL Entry",
			fields=["name", "to_rename"],
			filters={"voucher_type": "Journal Entry", "voucher_no": je.name},
			order_by="creation",
		)
		self.assertTrue(all(entry.to_rename == 0 for entry in gl_entries))

		# test that the deferring job does not influence non-deferred documents
		rename_gle_sle_docs()

		new_gl_entries = frappe.get_all(
			"GL Entry",
			fields=["name", "to_rename"],
			filters={"voucher_type": "Journal Entry", "voucher_no": je.name},
			order_by="creation",
		)

		self.assertTrue(all(new.name == old.name for new, old in zip(gl_entries, new_gl_entries, strict=False)))
		self.assertTrue(all(entry.to_rename == 0 for entry in new_gl_entries))

		new_naming_series_current_value = frappe.db.sql(
			"SELECT current from tabSeries where name = %s", naming_series
		)[0][0]
		# Assert +2, since each Journal Entry creates 2 GL entries
		# This asserts that the deferring job does not change the increment value
		self.assertEqual(old_naming_series_current_value + 2, new_naming_series_current_value)
