# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import flt, formatdate, getdate, today

from erpnext.accounts.doctype.finance_book.test_finance_book import create_finance_book
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.period_closing_voucher.period_closing_voucher import (
	aggregate_partial_result,
	get_period_start_end_date,
	process_date_range,
	summarize_and_post_ledger,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.general_ledger import make_reverse_gl_entries
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestPeriodClosingVoucher(ERPNextTestSuite):
	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("Accounts Settings", "use_legacy_controller_for_pcv", 1)

	def test_closing_entry(self):
		cost_center = create_cost_center("Test Cost Center 1")

		jv1 = make_journal_entry(
			posting_date="2021-03-15",
			amount=400,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center,
			company="Test PCV Company",
			save=False,
		)
		jv1.company = "Test PCV Company"
		jv1.save()
		jv1.submit()

		jv2 = make_journal_entry(
			posting_date="2021-03-15",
			amount=600,
			account1="Cost of Goods Sold - TPC",
			account2="Cash - TPC",
			cost_center=cost_center,
			company="Test PCV Company",
			save=False,
		)
		jv2.company = "Test PCV Company"
		jv2.save()
		jv2.submit()

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31")
		surplus_account = pcv.closing_account_head

		expected_gle = (
			("Cost of Goods Sold - TPC", 0.0, 600.0),
			(surplus_account, 200.0, 0.0),
			("Sales - TPC", 400.0, 0.0),
		)

		pcv_gle = [
			tuple(row)
			for row in frappe.get_all(
				"GL Entry",
				filters={"voucher_no": pcv.name},
				fields=["account", "debit", "credit"],
				order_by="account",
				as_list=True,
			)
		]
		pcv.reload()
		self.assertEqual(pcv.gle_processing_status, "Completed")
		self.assertEqual(tuple(pcv_gle), expected_gle)

	def test_trial_balance_pl_opening_starts_at_fiscal_year_after_closing(self):
		from erpnext.accounts.report.trial_balance.trial_balance import execute

		for posting_date, amount in (("2021-03-15", 400), ("2022-02-10", 150)):
			jv = make_journal_entry(
				posting_date=posting_date,
				amount=amount,
				account1="Cash - TPC",
				account2="Sales - TPC",
				cost_center=create_cost_center("Test Cost Center 1"),
				company="Test PCV Company",
				save=False,
			)
			jv.company = "Test PCV Company"
			jv.submit()
		self.make_period_closing_voucher(posting_date="2021-12-31")

		def sales_row(from_date):
			filters = frappe._dict(
				company="Test PCV Company",
				fiscal_year=get_fiscal_year("2022-06-30", company="Test PCV Company")[0],
				from_date=from_date,
				to_date="2022-12-31",
			)
			return next(row for row in execute(filters)[1] if row.get("account") == "Sales - TPC")

		row = sales_row("2022-01-01")
		self.assertEqual((row["opening_credit"], row["closing_credit"]), (0, 150))
		row = sales_row("2022-03-01")
		self.assertEqual((row["opening_credit"], row["closing_credit"]), (150, 150))

	def test_closing_needs_the_previous_closing_to_be_completed(self):
		pcv = self.make_period_closing_voucher(posting_date="2021-12-31")
		pcv.db_set("gle_processing_status", "Failed")

		# the next closing can be drafted, but not submitted
		next_pcv = self.make_period_closing_voucher(posting_date="2022-12-31", submit=False)
		with self.assertRaises(frappe.ValidationError):
			next_pcv.submit()

	def test_cost_center_wise_posting(self):
		surplus_account = create_account()

		cost_center1 = create_cost_center("Main")
		cost_center2 = create_cost_center("Western Branch")

		create_sales_invoice(
			company="Test PCV Company",
			cost_center=cost_center1,
			income_account="Sales - TPC",
			expense_account="Cost of Goods Sold - TPC",
			rate=400,
			debit_to="Debtors - TPC",
			currency="USD",
			customer="_Test Customer USD",
			posting_date="2021-03-15",
		)
		create_sales_invoice(
			company="Test PCV Company",
			cost_center=cost_center2,
			income_account="Sales - TPC",
			expense_account="Cost of Goods Sold - TPC",
			rate=200,
			debit_to="Debtors - TPC",
			currency="USD",
			customer="_Test Customer USD",
			posting_date="2021-03-15",
		)

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31", submit=False)
		pcv.save()
		pcv.submit()
		surplus_account = pcv.closing_account_head

		expected_gle = (
			(surplus_account, 0.0, 400.0, cost_center1),
			(surplus_account, 0.0, 200.0, cost_center2),
			("Sales - TPC", 400.0, 0.0, cost_center1),
			("Sales - TPC", 200.0, 0.0, cost_center2),
		)

		pcv_gle = [
			tuple(row)
			for row in frappe.get_all(
				"GL Entry",
				filters={"voucher_no": pcv.name},
				fields=["account", "debit", "credit", "cost_center"],
				order_by="account, cost_center",
				as_list=True,
			)
		]

		self.assertSequenceEqual(pcv_gle, expected_gle)

		pcv.reload()
		pcv.cancel()

		self.assertFalse(
			frappe.db.get_value(
				"GL Entry",
				{"voucher_type": "Period Closing Voucher", "voucher_no": pcv.name, "is_cancelled": 0},
			)
		)

	def test_period_closing_with_finance_book_entries(self):
		surplus_account = create_account()
		cost_center = create_cost_center("Test Cost Center 1")

		create_sales_invoice(
			company="Test PCV Company",
			income_account="Sales - TPC",
			expense_account="Cost of Goods Sold - TPC",
			cost_center=cost_center,
			rate=400,
			debit_to="Debtors - TPC",
			currency="USD",
			customer="_Test Customer USD",
			posting_date="2021-03-15",
		)

		jv = make_journal_entry(
			account1="Cash - TPC",
			account2="Sales - TPC",
			amount=400,
			cost_center=cost_center,
			posting_date="2021-03-15",
			company="Test PCV Company",
		)
		jv.company = "Test PCV Company"
		jv.finance_book = create_finance_book().name
		jv.save()
		jv.submit()

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31")
		surplus_account = pcv.closing_account_head

		expected_gle = (
			(surplus_account, 0.0, 400.0, None),
			(surplus_account, 0.0, 400.0, jv.finance_book),
			("Sales - TPC", 400.0, 0.0, None),
			("Sales - TPC", 400.0, 0.0, jv.finance_book),
		)

		pcv_gle = [
			tuple(row)
			for row in frappe.get_all(
				"GL Entry",
				filters={"voucher_no": pcv.name},
				fields=["account", "debit", "credit", "finance_book"],
				order_by="account, finance_book",
				as_list=True,
			)
		]

		# compare order-independently: postgres and MariaDB order NULL finance_book differently
		self.assertSequenceEqual(sorted(pcv_gle, key=str), sorted(expected_gle, key=str))

	def test_gl_entries_restrictions(self):
		cost_center = create_cost_center("Test Cost Center 1")

		self.make_period_closing_voucher(posting_date="2021-03-31")

		jv1 = make_journal_entry(
			posting_date="2021-03-15",
			amount=400,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center,
			company="Test PCV Company",
			save=False,
		)
		jv1.company = "Test PCV Company"
		jv1.save()

		self.assertRaises(frappe.ValidationError, jv1.submit)

	def test_closing_balance_with_dimensions_and_test_reposting_entry(self):
		cost_center1 = create_cost_center("Test Cost Center 1")
		cost_center2 = create_cost_center("Test Cost Center 2")

		jv1 = make_journal_entry(
			posting_date="2021-03-15",
			amount=400,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center1,
			company="Test PCV Company",
			save=False,
		)
		jv1.company = "Test PCV Company"
		jv1.save()
		jv1.submit()

		jv2 = make_journal_entry(
			posting_date="2021-03-15",
			amount=200,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center2,
			company="Test PCV Company",
			save=False,
		)
		jv2.company = "Test PCV Company"
		jv2.save()
		jv2.submit()

		pcv1 = self.make_period_closing_voucher(posting_date="2021-03-31")

		closing_balance = frappe.db.get_value(
			"Account Closing Balance",
			{
				"account": "Sales - TPC",
				"cost_center": cost_center1,
				"period_closing_voucher": pcv1.name,
				"is_period_closing_voucher_entry": 0,
			},
			["credit", "credit_in_account_currency"],
			as_dict=1,
		)

		self.assertEqual(closing_balance.credit, 400)
		self.assertEqual(closing_balance.credit_in_account_currency, 400)

		jv3 = make_journal_entry(
			posting_date="2022-03-15",
			amount=300,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center2,
			company="Test PCV Company",
			save=False,
		)

		jv3.company = "Test PCV Company"
		jv3.save()
		jv3.submit()

		pcv2 = self.make_period_closing_voucher(posting_date="2022-03-31")

		cc1_closing_balance = frappe.db.get_value(
			"Account Closing Balance",
			{
				"account": "Sales - TPC",
				"cost_center": cost_center1,
				"period_closing_voucher": pcv2.name,
				"is_period_closing_voucher_entry": 0,
			},
			["credit", "credit_in_account_currency"],
			as_dict=1,
		)

		cc2_closing_balance = frappe.db.get_value(
			"Account Closing Balance",
			{
				"account": "Sales - TPC",
				"cost_center": cost_center2,
				"period_closing_voucher": pcv2.name,
				"is_period_closing_voucher_entry": 0,
			},
			["credit", "credit_in_account_currency"],
			as_dict=1,
		)

		self.assertEqual(cc1_closing_balance.credit, 400)
		self.assertEqual(cc1_closing_balance.credit_in_account_currency, 400)
		self.assertEqual(cc2_closing_balance.credit, 500)
		self.assertEqual(cc2_closing_balance.credit_in_account_currency, 500)

		warehouse = frappe.db.get_value("Warehouse", {"company": "Test PCV Company"}, "name")

		repost_doc = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"company": "Test PCV Company",
				"posting_date": "2020-03-15",
				"based_on": "Item and Warehouse",
				"item_code": "Test Item 1",
				"warehouse": warehouse,
			}
		)

		self.assertRaises(frappe.ValidationError, repost_doc.save)

		repost_doc.posting_date = today()
		repost_doc.save()

	def test_dimension_grouped_opening_balance_matches_gl_scan(self):
		"""
		A dimension-grouped Balance Sheet must produce identical per-dimension
		figures whether opening balances come from

		- Account Closing Balance (the fast path) or
		- from a full GL scan (the fallback).
		"""
		from frappe.utils import add_days, getdate

		from erpnext.accounts.report.balance_sheet.balance_sheet import execute
		from erpnext.accounts.report.financial_statements import build_period_list

		company = "Test PCV Company"
		cc1 = create_cost_center("Test Cost Center 1")
		cc2 = create_cost_center("Test Cost Center 2")

		# Post to two cost centers, then close the year so balances land in Account Closing Balance.
		for amount, cost_center in ((400, cc1), (200, cc2)):
			jv = make_journal_entry(
				posting_date="2021-03-15",
				amount=amount,
				account1="Cash - TPC",
				account2="Sales - TPC",
				cost_center=cost_center,
				company=company,
				save=False,
			)
			jv.company = company
			jv.save()
			jv.submit()

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31")
		report_date = add_days(getdate(pcv.period_end_date), 1)

		report_filters = frappe._dict(
			company=company,
			period_start_date=report_date,
			period_end_date=report_date,
			periodicity="Yearly",
			filter_based_on="Date Range",
			accumulated_values=True,
			group_by_dimension="Cost Center",
		)

		period_list = build_period_list(report_filters)
		period_keys = [p.key for p in period_list]

		def key_for(cost_center):
			return next(p.key for p in period_list if p.dimension_value == cost_center)

		def figures(data):
			return {
				row["account_name"]: {k: row.get(k) for k in period_keys}
				for row in data
				if row.get("account_name")
			}

		# Fast path: opening balance sourced from Account Closing Balance.
		acb_figures = figures(execute(report_filters)[1])

		# Fallback: force a full GL scan and expect the same numbers.
		with self.change_settings("Accounts Settings", {"ignore_account_closing_balance": 1}):
			gl_figures = figures(execute(report_filters)[1])

		self.assertEqual(acb_figures, gl_figures)

		# the fast path must carry per-dimension opening balances, not aggregates or zeros
		self.assertEqual(acb_figures["Cash"][key_for(cc1)], 400)
		self.assertEqual(acb_figures["Cash"][key_for(cc2)], 200)

	def test_stock_validations_before_period_closing(self):
		from unittest.mock import patch

		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		create_custom_fields(
			{
				"Stock Closing Entry": [
					{
						"fieldname": "warehouse",
						"label": "Warehouse",
						"fieldtype": "Link",
						"options": "Warehouse",
					}
				]
			}
		)

		item = make_item("Test PCV Stock Item", {"is_stock_item": 1})
		se = make_stock_entry(
			item_code=item.name,
			qty=10,
			rate=100,
			to_warehouse="Stores - TPC",
			company="Test PCV Company",
			posting_date="2021-03-15",
		)

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31", submit=False)
		self.assertRaisesRegex(frappe.ValidationError, "Create a Stock Closing Entry", pcv.submit)

		sce = frappe.get_doc(
			{
				"doctype": "Stock Closing Entry",
				"company": "Test PCV Company",
				"from_date": pcv.period_start_date,
				"to_date": pcv.period_end_date,
				"warehouse": "Stores - TPC",
			}
		).insert()

		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			sce.submit()

		sce.db_set("status", "Completed")

		pcv.reload()
		self.assertRaisesRegex(frappe.ValidationError, "Create a Stock Closing Entry", pcv.submit)

		frappe.db.set_value("Stock Closing Entry", sce.name, {"warehouse": None, "status": "In Progress"})

		pcv.reload()
		self.assertRaisesRegex(frappe.ValidationError, "is not completed yet", pcv.submit)

		sce.create_stock_closing_balance_entries()
		sce.db_set("status", "Completed")

		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": se.name},
			["name", "stock_value_difference"],
			as_dict=1,
		)
		frappe.db.set_value(
			"Stock Ledger Entry", sle.name, "stock_value_difference", sle.stock_value_difference + 100
		)

		pcv.reload()
		self.assertRaisesRegex(frappe.ValidationError, "does not match", pcv.submit)

		frappe.db.set_value(
			"Stock Ledger Entry", sle.name, "stock_value_difference", sle.stock_value_difference
		)

		pcv.reload()
		self.assertRaisesRegex(frappe.ValidationError, "Regenerate", pcv.submit)

		self.rebuild_stock_closing_balance(sce)
		pcv.reload()
		pcv.submit()
		self.assertEqual(pcv.docstatus, 1)

	def test_stock_value_difference_within_tolerance_needs_confirmation(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item("Test PCV Tolerance Item", {"is_stock_item": 1})
		se = make_stock_entry(
			item_code=item.name,
			qty=10,
			rate=100,
			to_warehouse="Stores - TPC",
			company="Test PCV Company",
			posting_date="2021-03-15",
		)

		sle = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": se.name}, ["name", "stock_value_difference"], as_dict=1
		)
		frappe.db.set_value(
			"Stock Ledger Entry", sle.name, "stock_value_difference", sle.stock_value_difference + 5
		)

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31", submit=False)
		self.assertRaisesRegex(frappe.ValidationError, "does not match", pcv.submit)

		result = pcv.get_stock_value_difference()
		self.assertEqual(result["difference"], -5)
		self.assertTrue(result["within_tolerance"])

		frappe.db.set_value(
			"Stock Ledger Entry", sle.name, "stock_value_difference", sle.stock_value_difference + 100
		)

		pcv.reload()
		result = pcv.get_stock_value_difference()
		self.assertFalse(result["within_tolerance"])

		pcv.stock_value_difference = result["difference"]
		self.assertRaisesRegex(frappe.ValidationError, "does not match", pcv.submit)

		frappe.db.set_value(
			"Stock Ledger Entry", sle.name, "stock_value_difference", sle.stock_value_difference + 5
		)
		self.make_completed_stock_closing_entry(pcv.period_start_date, pcv.period_end_date)

		pcv.reload()
		pcv.stock_value_difference = -5
		pcv.submit()

		pcv.reload()
		self.assertEqual(pcv.docstatus, 1)
		self.assertEqual(pcv.stock_value_difference, -5)

	def test_batch_valuation_seeded_from_stock_closing_after_period_closing(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
			get_batch_from_bundle,
		)
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item(
			"Test PCV Batch Item",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TPCVB.####",
			},
		)
		se1 = make_stock_entry(
			item_code=item.name,
			qty=10,
			rate=100,
			to_warehouse="Stores - TPC",
			company="Test PCV Company",
			posting_date="2021-03-15",
		)
		batch_no = get_batch_from_bundle(se1.items[0].serial_and_batch_bundle)
		make_stock_entry(
			item_code=item.name,
			qty=10,
			rate=200,
			to_warehouse="Stores - TPC",
			company="Test PCV Company",
			posting_date="2021-06-15",
			batch_no=batch_no,
		)

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31", submit=False)
		sce = self.make_completed_stock_closing_entry(pcv.period_start_date, pcv.period_end_date)
		pcv.reload()
		pcv.submit()

		outward = make_stock_entry(
			item_code=item.name,
			qty=5,
			from_warehouse="Stores - TPC",
			company="Test PCV Company",
			posting_date="2022-04-01",
			batch_no=batch_no,
		)
		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": outward.name, "is_cancelled": 0},
			"stock_value_difference",
		)
		self.assertEqual(flt(stock_value_difference, 2), -750.0)

		self.assertRaisesRegex(
			frappe.ValidationError,
			"frozen",
			make_stock_entry,
			item_code=item.name,
			qty=1,
			rate=100,
			to_warehouse="Stores - TPC",
			company="Test PCV Company",
			posting_date="2021-05-01",
		)
		self.assertRaisesRegex(frappe.ValidationError, "frozen", se1.cancel)
		self.assertRaisesRegex(frappe.ValidationError, "closed accounting period", sce.cancel)

	def test_period_closing_blocks_stale_stock_closing_entry(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item("Test PCV Stock Item", {"is_stock_item": 1})
		make_stock_entry(
			item_code=item.name,
			qty=10,
			rate=100,
			to_warehouse="Stores - TPC",
			company="Test PCV Company",
			posting_date="2021-03-15",
		)

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31", submit=False)
		sce = self.make_completed_stock_closing_entry(pcv.period_start_date, pcv.period_end_date)

		make_stock_entry(
			item_code=item.name,
			qty=5,
			rate=100,
			to_warehouse="Stores - TPC",
			company="Test PCV Company",
			posting_date="2021-05-01",
		)

		pcv.reload()
		self.assertRaisesRegex(frappe.ValidationError, "Regenerate", pcv.submit)

		self.rebuild_stock_closing_balance(sce)
		pcv.reload()
		pcv.submit()
		self.assertEqual(pcv.docstatus, 1)

	def make_completed_stock_closing_entry(self, from_date, to_date):
		from unittest.mock import patch

		sce = frappe.get_doc(
			{
				"doctype": "Stock Closing Entry",
				"company": "Test PCV Company",
				"from_date": from_date,
				"to_date": to_date,
			}
		).insert()

		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			sce.submit()

		sce.create_stock_closing_balance_entries()
		sce.db_set("status", "Completed")
		return sce

	def rebuild_stock_closing_balance(self, sce):
		sce.remove_stock_closing()
		sce.create_stock_closing_balance_entries()
		sce.db_set("status", "Completed")

	def make_period_closing_voucher(
		self, posting_date, submit=True, period_start_date=None, period_end_date=None
	):
		surplus_account = create_account()
		cost_center = create_cost_center("Test Cost Center 1")
		fy = get_fiscal_year(posting_date, company="Test PCV Company")
		pcv = frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": posting_date or today(),
				"period_start_date": period_start_date or fy[1],
				"period_end_date": period_end_date or fy[2],
				"company": "Test PCV Company",
				"fiscal_year": fy[0],
				"cost_center": cost_center,
				"closing_account_head": surplus_account,
				"remarks": "test",
			}
		)
		pcv.insert()
		if submit:
			pcv.submit()

		return pcv

	@ERPNextTestSuite.change_settings(
		"Accounts Settings",
		{"enable_immutable_ledger": 1},
	)
	def test_immutable_ledger_reverse_entry_uses_passed_posting_date_after_pcv(self):
		cost_center = create_cost_center("Test Cost Center 1")

		jv = make_journal_entry(
			posting_date="2021-03-15",
			amount=400,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center,
			company="Test PCV Company",
			save=False,
		)
		jv.company = "Test PCV Company"
		jv.save()
		jv.submit()

		self.make_period_closing_voucher(posting_date="2021-03-31")

		frappe.db.set_value("Company", "Test PCV Company", "accounts_frozen_till_date", "2021-12-31")

		try:
			make_reverse_gl_entries(
				voucher_type="Journal Entry",
				voucher_no=jv.name,
			)
		finally:
			frappe.db.set_value("Company", "Test PCV Company", "accounts_frozen_till_date", None)

		totals_after_cancel = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Journal Entry", "voucher_no": jv.name, "is_cancelled": 0},
			fields=[{"SUM": "debit", "as": "total_debit"}, {"SUM": "credit", "as": "total_credit"}],
		)[0]

		self.assertEqual(totals_after_cancel.total_debit, totals_after_cancel.total_credit)

	def make_income_entry(self, posting_date, amount, income_account="Sales - TPC"):
		return make_journal_entry(
			posting_date=posting_date,
			amount=amount,
			account1="Cash - TPC",
			account2=income_account,
			cost_center=create_cost_center("Test Cost Center 1"),
			company="Test PCV Company",
			submit=True,
		)

	def test_partly_closed_previous_year_blocks_closing_next_year(self):
		self.make_income_entry("2021-02-10", 1000)
		self.make_income_entry("2021-06-15", 700)
		self.make_period_closing_voucher(
			posting_date="2021-02-28", period_start_date="2021-01-01", period_end_date="2021-02-28"
		)

		with self.assertRaisesRegex(frappe.ValidationError, f"from <strong>{formatdate('2021-03-01')}"):
			self.make_period_closing_voucher(posting_date="2022-12-31")

		self.make_period_closing_voucher(
			posting_date="2021-12-31", period_start_date="2021-03-01", period_end_date="2021-12-31"
		)
		self.make_period_closing_voucher(posting_date="2022-12-31")

	def test_unclosed_earlier_year_blocks_closing(self):
		self.make_income_entry("2021-06-15", 500)

		with self.assertRaisesRegex(frappe.ValidationError, f"from <strong>{formatdate('2021-06-15')}"):
			self.make_period_closing_voucher(posting_date="2023-12-31")

		self.make_period_closing_voucher(posting_date="2021-12-31")
		self.make_period_closing_voucher(posting_date="2023-12-31")

	def make_period_closing_voucher_with_mapreduce(self, posting_date):
		frappe.db.set_single_value("Accounts Settings", "use_legacy_controller_for_pcv", 0)
		with patch("frappe.utils.background_jobs.mapreduce"):
			pcv = self.make_period_closing_voucher(posting_date=posting_date)

		result = None
		for task in pcv.get_data_for_mapreduce():
			result = aggregate_partial_result(result, process_date_range(frappe._dict(task)))

		summarize_and_post_ledger(frappe.parse_json(frappe.as_json(result)), pcv.doctype, pcv.name)
		pcv.reload()
		return pcv

	def test_closing_error_fails_submit_in_legacy_controller(self):
		self.make_income_entry("2021-03-15", 1000, income_account="Service - TPC")
		frappe.db.set_value("Account", "Service - TPC", "disabled", 1)

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31", submit=False)
		with self.assertRaisesRegex(frappe.ValidationError, "disabled accounts"):
			pcv.submit()

	def test_closing_error_marks_voucher_failed_in_mapreduce_controller(self):
		self.make_income_entry("2021-03-15", 1000, income_account="Service - TPC")
		frappe.db.set_value("Account", "Service - TPC", "disabled", 1)

		pcv = self.make_period_closing_voucher_with_mapreduce(posting_date="2021-03-31")

		self.assertEqual(pcv.gle_processing_status, "Failed")
		self.assertIn("disabled accounts", pcv.error_message)
		self.assertFalse(frappe.db.exists("GL Entry", {"voucher_no": pcv.name}))
		self.assertFalse(frappe.db.exists("Account Closing Balance", {"period_closing_voucher": pcv.name}))

	def make_sale_and_refund(self, posting_date, amount):
		self.make_income_entry(posting_date, amount)
		self.make_income_entry(posting_date, -amount)

	def assert_period_closed_without_entries(self, pcv):
		self.assertEqual(pcv.gle_processing_status, "Completed")
		self.assertFalse(frappe.db.exists("GL Entry", {"voucher_no": pcv.name}))

		late_entry = make_journal_entry(
			posting_date="2021-12-20",
			amount=100,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=create_cost_center("Test Cost Center 1"),
			company="Test PCV Company",
		)
		self.assertRaisesRegex(frappe.ValidationError, "Books have been closed", late_entry.submit)

	def test_close_period_with_zero_profit_and_loss_in_legacy_controller(self):
		self.make_sale_and_refund("2021-03-15", 1000)
		pcv = self.make_period_closing_voucher(posting_date="2021-12-31")
		pcv.reload()
		self.assert_period_closed_without_entries(pcv)

	def test_close_period_with_zero_profit_and_loss_in_mapreduce_controller(self):
		self.make_sale_and_refund("2021-03-15", 1000)
		pcv = self.make_period_closing_voucher_with_mapreduce(posting_date="2021-12-31")
		self.assert_period_closed_without_entries(pcv)

	def get_balance_sheet_figure(self, account_name, period_end_date):
		from erpnext.accounts.report.balance_sheet.balance_sheet import execute
		from erpnext.accounts.report.financial_statements import build_period_list

		filters = frappe._dict(
			company="Test PCV Company",
			period_start_date=period_end_date,
			period_end_date=period_end_date,
			periodicity="Yearly",
			filter_based_on="Date Range",
			accumulated_values=True,
		)
		period_key = build_period_list(filters)[0].key
		return next(row[period_key] for row in execute(filters)[1] if row.get("account_name") == account_name)

	def get_gl_balance(self, account, to_date):
		return frappe.get_all(
			"GL Entry",
			filters={"account": account, "posting_date": ("<=", to_date), "is_cancelled": 0},
			fields=[{"SUM": "debit", "as": "debit"}, {"SUM": "credit", "as": "credit"}],
		)[0]

	def cancel_and_reclose_with_immutable_ledger(self, reclose):
		self.make_income_entry("2021-03-15", 1000)
		pcv = self.make_period_closing_voucher(posting_date="2021-12-31")
		pcv.cancel()

		reversal_dates = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": pcv.name, "remarks": ("like", "On cancellation%")},
			pluck="posting_date",
			distinct=True,
		)
		self.assertEqual(reversal_dates, [getdate("2021-12-31")])

		new_pcv = reclose(posting_date="2021-12-31")
		sales = self.get_gl_balance("Sales - TPC", "2021-12-31")
		self.assertEqual(flt(sales.debit) - flt(sales.credit), 0)
		self.assertEqual(self.get_balance_sheet_figure("Reserve and Surplus", "2021-12-31"), 1000)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry",
				{"voucher_no": new_pcv.name, "account": "Sales - TPC", "is_cancelled": 0},
				"debit",
			),
			1000,
		)

		map_step_rows = process_date_range(
			frappe._dict(
				from_date="2021-01-01",
				to_date="2021-12-31",
				pcv=new_pcv.name,
				report_type="Profit and Loss",
				balance_type="Normal Balance",
			)
		)
		sales = next(row for row in map_step_rows if row.account == "Sales - TPC")
		self.assertEqual((sales.debit, sales.credit), (0, 1000))

	@ERPNextTestSuite.change_settings("Accounts Settings", {"enable_immutable_ledger": 1})
	def test_immutable_ledger_cancel_and_reclose_in_legacy_controller(self):
		self.cancel_and_reclose_with_immutable_ledger(self.make_period_closing_voucher)

	@ERPNextTestSuite.change_settings("Accounts Settings", {"enable_immutable_ledger": 1})
	def test_immutable_ledger_cancel_and_reclose_in_mapreduce_controller(self):
		self.cancel_and_reclose_with_immutable_ledger(self.make_period_closing_voucher_with_mapreduce)

	def test_closing_account_must_be_usable_ledger_of_company(self):
		self.make_income_entry("2021-03-15", 1000)
		pcv = self.make_period_closing_voucher(posting_date="2021-12-31", submit=False)
		frappe.db.set_value("Company", "Test PCV Company", "role_allowed_for_frozen_entries", None)

		cases = [
			("Equity - TPC", {}, "cannot be a group account"),
			("Retained Earnings - _TC", {}, "does not belong to Company"),
			(pcv.closing_account_head, {"disabled": 1}, "is disabled"),
			(pcv.closing_account_head, {"disabled": 0, "freeze_account": "Yes"}, "is frozen"),
		]
		for account, values, message in cases:
			with self.subTest(account=account, values=values):
				if values:
					frappe.db.set_value("Account", account, values)

				pcv.reload()
				pcv.closing_account_head = account
				self.assertRaisesRegex(frappe.ValidationError, message, pcv.save)

	def make_foreign_currency_income_entry(self, posting_date, account, amount, exchange_rate):
		jv = frappe.new_doc("Journal Entry")
		jv.update({"posting_date": posting_date, "company": "Test PCV Company", "multi_currency": 1})
		income_side = "credit" if amount > 0 else "debit"
		cash_side = "debit" if amount > 0 else "credit"
		for row in (
			{"account": "Cash - TPC", f"{cash_side}_in_account_currency": abs(amount) * exchange_rate},
			{
				"account": account,
				"exchange_rate": exchange_rate,
				f"{income_side}_in_account_currency": abs(amount),
			},
		):
			jv.append("accounts", {**row, "cost_center": create_cost_center("Test Cost Center 1")})

		jv.submit()

	def get_account_currency_balance(self, account):
		balance = frappe.get_all(
			"GL Entry",
			filters={"account": account, "is_cancelled": 0},
			fields=[
				{"SUM": "debit", "as": "debit"},
				{"SUM": "credit", "as": "credit"},
				{"SUM": "debit_in_account_currency", "as": "debit_in_account_currency"},
				{"SUM": "credit_in_account_currency", "as": "credit_in_account_currency"},
			],
		)[0]
		return (
			flt(balance.debit) - flt(balance.credit),
			flt(balance.debit_in_account_currency) - flt(balance.credit_in_account_currency),
		)

	def close_and_cancel_foreign_currency_income(self, make_pcv):
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Sales EUR",
				"parent_account": "Direct Income - TPC",
				"company": "Test PCV Company",
				"account_currency": "EUR",
			}
		).insert(ignore_if_duplicate=True)
		self.make_foreign_currency_income_entry("2021-03-15", account.name, 100, 80)
		self.make_foreign_currency_income_entry("2021-04-15", account.name, -80, 100)
		self.assertEqual(self.get_account_currency_balance(account.name), (0, -20))

		pcv = make_pcv(posting_date="2021-12-31")
		self.assertEqual(pcv.gle_processing_status, "Completed")
		self.assertEqual(self.get_account_currency_balance(account.name), (0, 0))

		pcv.cancel()
		self.assertEqual(self.get_account_currency_balance(account.name), (0, -20))

	@ERPNextTestSuite.change_settings("Accounts Settings", {"enable_immutable_ledger": 1})
	def test_close_foreign_currency_balance_in_legacy_controller(self):
		self.close_and_cancel_foreign_currency_income(self.make_period_closing_voucher)

	@ERPNextTestSuite.change_settings("Accounts Settings", {"enable_immutable_ledger": 1})
	def test_close_foreign_currency_balance_in_mapreduce_controller(self):
		self.close_and_cancel_foreign_currency_income(self.make_period_closing_voucher_with_mapreduce)

	def test_future_closing_voucher_message_shows_full_name(self):
		self.make_income_entry("2021-03-15", 1000)
		pcv = self.make_period_closing_voucher(posting_date="2021-12-31")
		next_pcv = self.make_period_closing_voucher(posting_date="2022-12-31")

		self.assertRaisesRegex(
			frappe.ValidationError, f"Period Closing Entry {next_pcv.name} exists after", pcv.cancel
		)

	def test_period_dates_need_read_permission(self):
		from erpnext.crm.doctype.lead.test_lead import make_user

		user = make_user("pcv_stock_user@example.com", "Stock User")
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(user)

		self.assertRaises(
			frappe.PermissionError, get_period_start_end_date, "_Test Fiscal Year 2021", "Test PCV Company"
		)

	def test_period_dates_need_permission_on_requested_company(self):
		from frappe.permissions import add_user_permission

		from erpnext.crm.doctype.lead.test_lead import make_user

		user = make_user("pcv_restricted_accounts_manager@example.com", "Accounts Manager")
		add_user_permission("Company", "_Test Company", user)

		with self.set_user(user):
			get_period_start_end_date("_Test Fiscal Year 2021", "_Test Company")
			self.assertRaises(
				frappe.PermissionError,
				get_period_start_end_date,
				"_Test Fiscal Year 2021",
				"Test PCV Company",
			)

	def test_incomplete_previous_closing_blocks_next_closing(self):
		self.make_income_entry("2021-03-15", 1000, income_account="Service - TPC")
		frappe.db.set_value("Account", "Service - TPC", "disabled", 1)
		failed_pcv = self.make_period_closing_voucher_with_mapreduce(posting_date="2021-12-31")
		self.assertEqual(failed_pcv.gle_processing_status, "Failed")

		frappe.db.set_single_value("Accounts Settings", "use_legacy_controller_for_pcv", 1)
		with self.assertRaisesRegex(frappe.ValidationError, f"{failed_pcv.name}.*GL Entry Processing Status"):
			self.make_period_closing_voucher(posting_date="2022-12-31")


def create_account():
	account = frappe.get_doc(
		{
			"account_name": "Reserve and Surplus",
			"is_group": 0,
			"company": "Test PCV Company",
			"root_type": "Liability",
			"report_type": "Balance Sheet",
			"account_currency": "USD",
			"parent_account": "Current Liabilities - TPC",
			"doctype": "Account",
		}
	).insert(ignore_if_duplicate=True)
	return account.name


def create_cost_center(cc_name):
	costcenter = frappe.get_doc(
		{
			"company": "Test PCV Company",
			"cost_center_name": cc_name,
			"doctype": "Cost Center",
			"parent_cost_center": "Test PCV Company - TPC",
		}
	)
	costcenter.insert(ignore_if_duplicate=True)
	return costcenter.name
