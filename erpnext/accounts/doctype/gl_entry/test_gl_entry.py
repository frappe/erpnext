# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.model.naming import parse_naming_series
from frappe.utils import add_days, flt, getdate, nowdate

from erpnext.accounts.doctype.account_closing_balance.account_closing_balance import (
	set_amount_in_reporting_currency,
)
from erpnext.accounts.doctype.accounting_period.test_accounting_period import create_accounting_period
from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
from erpnext.accounts.doctype.gl_entry.gl_entry import rename_gle_sle_docs
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.general_ledger import make_round_off_gle
from erpnext.accounts.utils import get_fiscal_year
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

	def test_existing_round_off_entry_is_kept_for_one_cent_imbalance(self):
		frappe.db.set_value("Company", "_Test Company", "round_off_account", "_Test Write Off - _TC")
		frappe.db.set_value("Company", "_Test Company", "round_off_cost_center", "_Test Cost Center - _TC")

		def make_entry(account, debit=0, credit=0):
			return frappe._dict(
				voucher_type="Journal Entry",
				voucher_no="_Test Round Off JV",
				company="_Test Company",
				posting_date="2024-01-01",
				remarks="",
				is_opening="No",
				account=account,
				debit=debit,
				credit=credit,
				debit_in_account_currency=debit,
				credit_in_account_currency=credit,
			)

		round_off_gle = make_entry("_Test Write Off - _TC", debit=0.03)
		gl_map = [
			make_entry("_Test Account Cost for Goods Sold - _TC", debit=100),
			make_entry("_Test Bank - _TC", credit=100.01),
			round_off_gle,
		]

		# total debit - credit = 100.03 - 100.01 = 0.02
		make_round_off_gle(gl_map, 0.02, 0.02, 2)

		self.assertIn(round_off_gle, gl_map)
		self.assertEqual(round_off_gle.debit, 0.01)
		self.assertEqual(round_off_gle.credit, 0)
		self.assertEqual(flt(sum(d.debit - d.credit for d in gl_map), 2), 0)

	def test_two_round_off_rows_are_balanced(self):
		frappe.db.set_value("Company", "_Test Company", "round_off_account", "_Test Write Off - _TC")
		frappe.db.set_value("Company", "_Test Company", "round_off_cost_center", "_Test Cost Center - _TC")

		def make_entry(account, debit=0, credit=0):
			return frappe._dict(
				voucher_type="Journal Entry",
				voucher_no="_Test Round Off JV",
				company="_Test Company",
				posting_date="2024-01-01",
				remarks="",
				is_opening="No",
				account=account,
				debit=debit,
				credit=credit,
				debit_in_account_currency=debit,
				credit_in_account_currency=credit,
			)

		gl_map = [
			make_entry("_Test Account Cost for Goods Sold - _TC", debit=100),
			make_entry("_Test Write Off - _TC", debit=0.03),
			make_entry("_Test Write Off - _TC", debit=0.04),
			make_entry("_Test Bank - _TC", credit=100.06),
		]

		# total debit - credit = 100.07 - 100.06 = 0.01
		make_round_off_gle(gl_map, 0.01, 0.01, 2)

		self.assertEqual(flt(sum(d.debit - d.credit for d in gl_map), 2), 0)

	def test_disabled_cost_center_is_refused(self):
		create_cost_center(cost_center_name="_Test GL Disabled Cost Center")
		cost_center = "_Test GL Disabled Cost Center - _TC"
		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC", "_Test Bank - _TC", 100, cost_center, submit=True
		)
		frappe.db.set_value("Cost Center", cost_center, "disabled", 1)
		self.addCleanup(frappe.db.set_value, "Cost Center", cost_center, "disabled", 0)

		self.assertRaisesRegex(
			frappe.ValidationError,
			"is disabled",
			make_journal_entry,
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			100,
			cost_center,
			submit=True,
		)

		# entries posted before the cost center was disabled can still be reversed
		with self.change_settings("Accounts Settings", {"enable_immutable_ledger": 1}):
			jv.cancel()

		balance = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": jv.name, "is_cancelled": 0},
			fields=[{"SUM": "debit"}, {"SUM": "credit"}],
			as_list=True,
		)[0]
		self.assertEqual(balance[0], balance[1])

	def test_rename_hooks_are_called_for_their_doctype(self):
		make_journal_entry("_Test Account Cost for Goods Sold - _TC", "_Test Bank - _TC", 100, submit=True)
		get_hooks = frappe.get_hooks

		def hooks(hook=None, *args, **kwargs):
			if hook in ("on_gle_rename", "on_sle_rename"):
				return [f"test.{hook}"]
			return get_hooks(hook, *args, **kwargs)

		with patch("frappe.get_hooks", side_effect=hooks), patch("frappe.call") as call:
			rename_gle_sle_docs()

		renamed = {c.args[0]: [] for c in call.call_args_list}
		for c in call.call_args_list:
			renamed[c.args[0]].append(c.kwargs["newname"])

		self.assertTrue(renamed.get("test.on_gle_rename"))
		self.assertTrue(all(frappe.db.exists("GL Entry", name) for name in renamed["test.on_gle_rename"]))
		self.assertFalse(
			any(frappe.db.exists("GL Entry", name) for name in renamed.get("test.on_sle_rename", []))
		)

	@ERPNextTestSuite.change_settings("Accounts Settings", {"enable_immutable_ledger": 1})
	def test_immutable_reversal_date_and_fiscal_year(self):
		previous_year_end = add_days(get_fiscal_year(nowdate(), company="_Test Company")[1], -1)
		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			100,
			posting_date=previous_year_end,
			submit=True,
		)

		# the period of the original voucher is closed after it was posted
		period = create_accounting_period(
			start_date=previous_year_end, end_date=previous_year_end, period_name="_Test GL Reversal Period"
		)
		period.closed_documents[0].document_type = "Journal Entry"
		period.insert()
		jv.cancel()

		reversal = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": jv.name, "posting_date": ["!=", previous_year_end]},
			fields=["posting_date", "fiscal_year"],
		)
		self.assertEqual(len(reversal), 2)
		for row in reversal:
			self.assertEqual(row.posting_date, getdate())
			self.assertEqual(row.fiscal_year, get_fiscal_year(nowdate(), company="_Test Company")[0])

	@ERPNextTestSuite.change_settings("Accounts Settings", {"enable_immutable_ledger": 1})
	def test_immutable_reversal_is_not_dated_before_voucher(self):
		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC", "_Test Bank - _TC", 100, submit=True
		)
		frappe.form_dict.posting_date = add_days(nowdate(), -10)
		self.addCleanup(frappe.form_dict.pop, "posting_date", None)
		jv.cancel()

		posting_dates = frappe.get_all("GL Entry", filters={"voucher_no": jv.name}, pluck="posting_date")
		self.assertEqual(len(posting_dates), 4)
		self.assertEqual(set(posting_dates), {getdate(jv.posting_date)})

	def test_cancelling_deferred_journal_keeps_invoice_outstanding(self):
		payment = create_payment_entry(
			payment_type="Receive",
			party_type="Customer",
			party="_Test Customer",
			paid_from="Debtors - _TC",
			paid_to="_Test Bank - _TC",
			paid_amount=100,
			save=True,
			submit=True,
		)
		si = create_sales_invoice(rate=100, do_not_submit=True)
		si.append(
			"advances",
			{
				"reference_type": "Payment Entry",
				"reference_name": payment.name,
				"advance_amount": 100,
				"allocated_amount": 100,
			},
		)
		si.items[0].deferred_revenue_account = "_Test Write Off - _TC"
		si.save().submit()
		self.assertEqual(si.outstanding_amount, 0)

		jv = frappe.new_doc("Journal Entry")
		jv.voucher_type = "Deferred Revenue"
		jv.company = si.company
		jv.posting_date = si.posting_date
		for account, field in (
			(si.items[0].deferred_revenue_account, "debit"),
			(si.items[0].income_account, "credit"),
		):
			jv.append(
				"accounts",
				{
					"account": account,
					f"{field}_in_account_currency": 10,
					"cost_center": si.items[0].cost_center,
					"reference_type": "Sales Invoice",
					"reference_name": si.name,
					"reference_detail_no": si.items[0].name,
				},
			)
		jv.submit()
		jv.cancel()

		self.assertEqual(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"), 0)

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
