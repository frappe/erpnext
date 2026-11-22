# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The public functions of section 7.2, and the facts of section 18 that the calculation relies on."""

import ast
import os

import frappe

from erpnext.accounts.cash_basis import get_cash_adjustments
from erpnext.accounts.cash_basis.settlements import get_settlement_events
from erpnext.accounts.cash_basis.tests.cash_basis_case import CashBasisTestCase
from erpnext.accounts.cash_basis.tests.fixtures import CUSTOMER, US_COMPANY, acc
from erpnext.accounts.cash_basis.tests.vouchers import line, make_journal_entry, make_sales_invoice, pay, save
from erpnext.tests.utils import change_settings

SALES = acc("Sales")
DEBTORS = acc("Debtors")
TAX = acc("ST 6%")


CALCULATION_MODULES = (
	"adjustments",
	"calculation",
	"exceptions",
	"filters",
	"obligations",
	"queries",
	"settlements",
)
PACKAGE = "erpnext.accounts.cash_basis"


class TestCalculationStandsAlone(CashBasisTestCase):
	"""Section 16.3, rule 2: the calculation does not import the Company form code or the report code."""

	def test_calculation_modules_import_no_setting_or_report_code(self):
		package_dir = os.path.dirname(os.path.dirname(__file__))
		forbidden = ("erpnext.setup", "erpnext.accounts.report", f"{PACKAGE}.settings")
		for module in CALCULATION_MODULES:
			with open(os.path.join(package_dir, f"{module}.py")) as source:
				tree = ast.parse(source.read())
			for node in ast.walk(tree):
				if isinstance(node, ast.Import):
					names = [alias.name for alias in node.names]
				elif isinstance(node, ast.ImportFrom):
					names = [node.module or ""]
					if node.module == PACKAGE:
						# Only submodules of the calculation may come from the package.
						for alias in node.names:
							self.assertIn(alias.name, CALCULATION_MODULES, f"{module} imports {alias.name}")
				else:
					continue
				for name in names:
					self.assertFalse(name.startswith(forbidden), f"{module} imports {name}")

	def test_calculation_reads_no_unapplied_setting(self):
		package_dir = os.path.dirname(os.path.dirname(__file__))
		for module in CALCULATION_MODULES:
			with open(os.path.join(package_dir, f"{module}.py")) as source:
				self.assertNotIn("unapplied_cash_", source.read(), module)


class TestCashBasisPublicFunctions(CashBasisTestCase):
	def test_adjustment_rows_have_report_keys(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		pay(invoice, "2026-04-10", 55)
		rows = get_cash_adjustments(US_COMPANY, "2026-04-30", group_by="row", filters={})
		for key in (
			"account",
			"posting_date",
			"debit",
			"credit",
			"fiscal_year",
			"cost_center",
			"is_cash_adjustment",
		):
			self.assertIn(key, rows[0])
		remarks = {row["remarks"] for row in rows}
		self.assertEqual(remarks, {"Cash basis: deferral", "Cash basis: recognition"})
		self.assertTrue(all(row["voucher_no"] == invoice.name for row in rows))
		self.assertEqual(
			{row["fiscal_year"] for row in rows},
			{frappe.db.get_value("Fiscal Year", {"year_start_date": "2026-01-01"})},
		)

		grouped = get_cash_adjustments(US_COMPANY, "2026-04-30", group_by="account", filters={})
		self.assertEqual(len(grouped), 4)  # two dates, two accounts
		self.assertNotIn("voucher_no", grouped[0])

		april = get_cash_adjustments(US_COMPANY, "2026-04-30", "2026-04-01", group_by="row", filters={})
		self.assertEqual({str(row["posting_date"]) for row in april}, {"2026-04-10"})

	def test_settlement_events(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		payment = pay(invoice, "2026-04-10", 55)
		events = get_settlement_events(US_COMPANY, "2026-04-30")
		self.assertEqual(len(events), 1)
		event = events[0]
		self.assertEqual(
			(event["against_voucher_no"], event["voucher_no"], event["settlement_class"]),
			(invoice.name, payment.name, "Cash"),
		)
		self.assertEqual((event["amount"], event["amount_in_account_currency"]), (55, 55))
		self.assertEqual(str(event["recognition_date"]), "2026-04-10")
		self.assertEqual(get_settlement_events(US_COMPANY, "2026-04-30", from_date="2026-05-01"), [])

	def test_write_off_is_non_cash_event(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		make_journal_entry(
			"2026-03-20",
			[
				{"account": acc("Write Off"), "debit": 100},
				{
					"account": DEBTORS,
					"credit": 100,
					"party_type": "Customer",
					"party": CUSTOMER,
					"reference_type": "Sales Invoice",
					"reference_name": invoice.name,
				},
			],
		)
		events = get_settlement_events(US_COMPANY, "2026-03-31")
		self.assertEqual([e["settlement_class"] for e in events], ["Non-cash"])

	def test_repost_with_immutable_ledger_keeps_the_result(self):
		"""Section 18, fact 3 (corrected): the repost adds duplicate and reversal rows. Net sums stay."""
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		pay(invoice, "2026-04-10", 55)
		before = self.cash_balances("2026-12-31")
		before_rows = frappe.db.count("Payment Ledger Entry", {"company": US_COMPANY, "delinked": 0})

		with change_settings("Accounts Settings", {"enable_immutable_ledger": 1}):
			repost = frappe.get_doc(
				{
					"doctype": "Repost Accounting Ledger",
					"company": US_COMPANY,
					"vouchers": [{"voucher_type": "Sales Invoice", "voucher_no": invoice.name}],
				}
			)
			save(repost, submit=True)

		self.assertGreater(
			frappe.db.count("Payment Ledger Entry", {"company": US_COMPANY, "delinked": 0}), before_rows
		)
		after = self.cash_balances("2026-12-31")
		for account in (SALES, TAX, DEBTORS):
			self.assertAlmostEqual(after[account], before[account], places=2)
		self.assertEqual(after[SALES], -50)
		self.assert_invariants("2026-12-31")
