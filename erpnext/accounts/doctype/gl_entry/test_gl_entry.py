# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model.naming import parse_naming_series

from erpnext.accounts.doctype.account_closing_balance.account_closing_balance import (
	set_amount_in_reporting_currency,
)
from erpnext.accounts.doctype.gl_entry.gl_entry import rename_gle_sle_docs
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestGLEntry(ERPNextTestSuite):
	def test_unregistered_party_type_is_rejected_without_a_party(self):
		entry = frappe.get_doc(doctype="GL Entry", account="Debtors - _TC", party_type="User", is_cancelled=0)
		self.assertRaises(frappe.ValidationError, entry.validate_party)

	def test_unregistered_party_type_on_untyped_account_is_rejected(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		account = create_account(
			account_name="_Test Party Type Untyped",
			parent_account=frappe.get_value("Account", "Debtors - _TC", "parent_account"),
			company="_Test Company",
		)
		entry = frappe.get_doc(
			doctype="GL Entry", account=account, party_type="User", party="Administrator", is_cancelled=0
		)
		self.assertRaises(frappe.ValidationError, entry.validate_party)
		entry.is_cancelled = 1
		entry.validate_party()

	@ERPNextTestSuite.change_settings("Accounts Settings", {"enable_immutable_ledger": 1})
	def test_immutable_ledger_can_reverse_historical_unregistered_party(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		account = create_account(
			account_name="_Test Historical Party Type",
			parent_account=frappe.get_value("Account", "Debtors - _TC", "parent_account"),
			company="_Test Company",
		)
		journal = make_journal_entry(account, "_Test Cash - _TC", 10, submit=True)
		entry = frappe.get_value("GL Entry", {"voucher_no": journal.name, "account": account}, "name")
		# Simulate a ledger entry posted before Party Type validation existed.
		frappe.db.set_value("GL Entry", entry, {"party_type": "User", "party": "Administrator"})
		frappe.db.set_value(
			"Journal Entry Account",
			journal.accounts[0].name,
			{"party_type": "User", "party": "Administrator"},
		)
		journal.reload()
		journal.cancel()
		entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": journal.name, "account": account, "is_cancelled": 0},
			fields=["debit", "credit", "party_type", "party"],
		)
		self.assertEqual(len(entries), 2)
		self.assertEqual(sum(row.debit - row.credit for row in entries), 0)
		self.assertTrue(all(row.party_type == "User" and row.party == "Administrator" for row in entries))

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

		round_off_entry = frappe.get_all(
			"GL Entry",
			filters={
				"voucher_type": "Journal Entry",
				"voucher_no": jv.name,
				"account": "_Test Write Off - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"debit": 0,
				"credit": 0.01,
			},
			pluck="name",
		)

		self.assertTrue(round_off_entry)

	def test_rename_entries(self):
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
		series = frappe.qb.DocType("Series")
		old_naming_series_current_value = (
			frappe.qb.from_(series).select(series["current"]).where(series.name == naming_series).run()
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

		new_naming_series_current_value = (
			frappe.qb.from_(series).select(series["current"]).where(series.name == naming_series).run()
		)[0][0]
		self.assertEqual(old_naming_series_current_value + 2, new_naming_series_current_value)

	def test_validate_account_party_type(self):
		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			100,
			"_Test Cost Center - _TC",
			save=False,
			submit=False,
		)

		for row in jv.accounts:
			row.party_type = "Supplier"
			break

		jv.save()
		try:
			jv.submit()
		except Exception as e:
			self.assertEqual(
				str(e),
				"Party Type and Party can only be set for Receivable / Payable account_Test Account Cost for Goods Sold - _TC",
			)

		jv1 = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			100,
			"_Test Cost Center - _TC",
			save=False,
			submit=False,
		)

		for row in jv.accounts:
			row.party_type = "Customer"
			break

		jv1.save()
		try:
			jv1.submit()
		except Exception as e:
			self.assertEqual(
				str(e),
				"Party Type and Party can only be set for Receivable / Payable account_Test Account Cost for Goods Sold - _TC",
			)

	def test_validate_account_party_type_shareholder(self):
		jv = make_journal_entry(
			"Opening Balance Equity - _TC",
			"Cash - _TC",
			100,
			"_Test Cost Center - _TC",
			save=False,
			submit=False,
		)

		for row in jv.accounts:
			row.party_type = "Shareholder"
			break

		jv.save().submit()
		self.assertEqual(1, jv.docstatus)

	def test_no_reporting_currency_conversion_without_reporting_currency(self):
		company = "_Test Company"
		frappe.db.set_value("Company", company, "reporting_currency", None)
		frappe.clear_document_cache("Company", company)
		self.addCleanup(frappe.clear_document_cache, "Company", company)

		je = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC", "_Test Bank - _TC", 100, submit=True
		)
		exchange_rates = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Journal Entry", "voucher_no": je.name},
			pluck="reporting_currency_exchange_rate",
		)
		self.assertTrue(exchange_rates)
		self.assertFalse(any(exchange_rates))

		closing_entry = frappe._dict(debit=100, credit=0)
		set_amount_in_reporting_currency(closing_entry, company, je.posting_date)
		self.assertEqual(closing_entry, {"debit": 100, "credit": 0})
