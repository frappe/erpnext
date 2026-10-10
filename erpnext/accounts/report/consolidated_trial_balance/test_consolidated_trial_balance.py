# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, today

from erpnext.accounts.report.consolidated_trial_balance.consolidated_trial_balance import execute
from erpnext.setup.utils import get_exchange_rate
from erpnext.tests.utils import ERPNextTestSuite


class ForeignCurrencyTranslationReserveNotFoundError(frappe.ValidationError):
	pass


class TestConsolidatedTrialBalance(ERPNextTestSuite):
	def setUp(self):
		from erpnext.accounts.utils import get_fiscal_year

		create_journal_entry(
			company="Parent Group Company India",
			acc1="Marketing Expenses - PGCI",
			acc2="Cash - PGCI",
			amount=100000,
		)

		create_journal_entry(
			company="Child Company India", acc1="Cash - CCI", acc2="Secured Loans - CCI", amount=50000
		)

		create_journal_entry(
			company="Child Company US", acc1="Marketing Expenses - CCU", acc2="Cash - CCU", amount=1000
		)

		self.fiscal_year = get_fiscal_year(today(), company="Parent Group Company India")[0]

	def test_single_company_report(self):
		filters = frappe._dict({"company": ["Parent Group Company India"], "fiscal_year": self.fiscal_year})

		report = execute(filters)
		total_row = report[1][-1]

		self.assertEqual(total_row["closing_debit"], total_row["closing_credit"])
		self.assertEqual(total_row["closing_credit"], 100000)

	def test_child_company_report_with_same_default_currency_as_parent_company(self):
		filters = frappe._dict(
			{
				"company": ["Parent Group Company India", "Child Company India"],
				"fiscal_year": self.fiscal_year,
			}
		)

		report = execute(filters)
		total_row = report[1][-1]

		self.assertEqual(total_row["closing_debit"], total_row["closing_credit"])

	def test_child_company_with_different_default_currency_from_parent_company(self):
		filters = frappe._dict(
			{
				"company": ["Parent Group Company India", "Child Company US"],
				"fiscal_year": self.fiscal_year,
			}
		)

		report = execute(filters)
		total_row = report[1][-1]

		exchange_rate = get_exchange_rate("USD", "INR")

		fctr = [d for d in report[1] if d.get("account") == _("Foreign Currency Translation Reserve")]

		if not fctr:
			raise ForeignCurrencyTranslationReserveNotFoundError

		ccu_total_credit = 1000 * flt(exchange_rate)

		self.assertEqual(total_row["closing_debit"], total_row["closing_credit"])
		self.assertNotEqual(total_row["closing_credit"], ccu_total_credit)

		self.assertEqual(total_row["closing_credit"], flt(100000 + ccu_total_credit))

	def test_company_needs_read_permission(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"{frappe.generate_hash(length=10)}@example.com",
				"first_name": "Consolidated Trial Balance Test",
				"send_welcome_email": 0,
				"roles": [{"role": "Accounts User"}],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user.name,
				"allow": "Company",
				"for_value": "_Test Company",
			}
		).insert(ignore_permissions=True)
		filters = frappe._dict({"company": ["Child Company US"], "fiscal_year": self.fiscal_year})

		frappe.set_user(user.name)
		try:
			self.assertRaises(frappe.PermissionError, execute, filters)
		finally:
			frappe.set_user("Administrator")

	def test_opening_balance_sheet_amounts_translated_at_closing_rate(self):
		year_start = frappe.db.get_value("Fiscal Year", self.fiscal_year, "year_start_date")
		set_usd_rate(year_start, 80)
		set_usd_rate(today(), 85)
		create_journal_entry(
			company="Child Company US",
			acc1="Cash - CCU",
			acc2="Marketing Expenses - CCU",
			amount=-100,
			posting_date=year_start,
		)

		usd_expenses_in_inr = sum(
			frappe.get_all(
				"GL Entry",
				filters={"account": "Marketing Expenses - CCU", "is_cancelled": 0},
				pluck="debit_in_reporting_currency",
			)
		)
		# Cash: 100000 INR plus 1100 USD at the closing rate of 85
		expected_cash_credit = 100000 + 1100 * 85
		expected_reserve_debit = expected_cash_credit - (100000 + usd_expenses_in_inr)

		for from_date in (year_start, add_days(year_start, 1)):
			filters = frappe._dict(
				{
					"company": ["Parent Group Company India", "Child Company US"],
					"fiscal_year": self.fiscal_year,
					"from_date": from_date,
				}
			)
			rows = {row.get("acc_name") or row.get("account"): row for row in execute(filters)[1]}
			cash, reserve = rows["Cash"], rows[_("Foreign Currency Translation Reserve")]

			self.assertEqual(cash["closing_credit"] - cash["closing_debit"], expected_cash_credit)
			self.assertEqual(reserve["closing_debit"] - reserve["closing_credit"], expected_reserve_debit)


def create_journal_entry(**args):
	args = frappe._dict(args)
	je = frappe.new_doc("Journal Entry")
	je.posting_date = args.posting_date or today()
	je.company = args.company

	je.set(
		"accounts",
		[
			{
				"account": args.acc1,
				"debit_in_account_currency": args.amount if args.amount > 0 else 0,
				"credit_in_account_currency": abs(args.amount) if args.amount < 0 else 0,
			},
			{
				"account": args.acc2,
				"credit_in_account_currency": args.amount if args.amount > 0 else 0,
				"debit_in_account_currency": abs(args.amount) if args.amount < 0 else 0,
			},
		],
	)
	je.save()
	je.submit()


def set_usd_rate(date, rate):
	frappe.db.delete(
		"Currency Exchange", {"date": getdate(date), "from_currency": "USD", "to_currency": "INR"}
	)
	frappe.get_doc(
		{
			"doctype": "Currency Exchange",
			"date": date,
			"from_currency": "USD",
			"to_currency": "INR",
			"exchange_rate": rate,
			"for_buying": 1,
			"for_selling": 1,
		}
	).insert()
