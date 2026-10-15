# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model.naming import parse_naming_series
from frappe.utils import flt

from erpnext.accounts.doctype.account_closing_balance.account_closing_balance import (
	set_amount_in_reporting_currency,
)
from erpnext.accounts.doctype.gl_entry.gl_entry import rename_gle_sle_docs
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.general_ledger import make_round_off_gle
from erpnext.tests.utils import ERPNextTestSuite


class TestGLEntry(ERPNextTestSuite):
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
