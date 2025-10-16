# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe import _
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, today

from erpnext.accounts.report.consolidated_trial_balance.consolidated_trial_balance import execute
from erpnext.setup.utils import get_exchange_rate


class ForeignCurrencyTranslationReserveNotFoundError(frappe.ValidationError):
	pass


class TestConsolidatedTrialBalance(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		from erpnext.accounts.report.trial_balance.test_trial_balance import create_company
		from erpnext.accounts.utils import get_fiscal_year

		# Group Company
		create_company(company_name="Parent Group Company India", is_group=1)

		create_company(company_name="Child Company India", parent_company="Parent Group Company India")

		# Child Company with different currency
		create_company(
			company_name="Child Company US",
			country="United States",
			currency="USD",
			parent_company="Parent Group Company India",
		)

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

		cls.fiscal_year = get_fiscal_year(today(), company="Parent Group Company India")[0]

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
