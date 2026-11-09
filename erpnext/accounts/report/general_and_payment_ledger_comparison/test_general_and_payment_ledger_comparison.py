from unittest.mock import patch

import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.general_and_payment_ledger_comparison.general_and_payment_ledger_comparison import (
	General_Payment_Ledger_Comparison,
	execute,
)
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestGeneralAndPaymentLedger(FrappeTestCase, AccountsTestMixin):
	def setUp(self):
		self.create_company()
		self.cleanup()

	def tearDown(self):
		frappe.db.rollback()

	def cleanup(self):
		doctypes = []
		doctypes.append(qb.DocType("GL Entry"))
		doctypes.append(qb.DocType("Payment Ledger Entry"))
		doctypes.append(qb.DocType("Sales Invoice"))

		for doctype in doctypes:
			qb.from_(doctype).delete().where(doctype.company == self.company).run()

	def test_01_basic_report_functionality(self):
		sinv = create_sales_invoice(
			company=self.company,
			debit_to=self.debit_to,
			expense_account=self.expense_account,
			cost_center=self.cost_center,
			income_account=self.income_account,
			warehouse=self.warehouse,
		)

		# manually edit the payment ledger entry
		ple = frappe.db.get_all("Payment Ledger Entry", filters={"voucher_no": sinv.name, "delinked": 0})[0]
		frappe.db.set_value("Payment Ledger Entry", ple.name, "amount", sinv.grand_total - 1)

		filters = frappe._dict({"company": self.company})
		columns, data = execute(filters=filters)
		self.assertEqual(len(data), 1)

		expected = {
			"company": sinv.company,
			"account": sinv.debit_to,
			"voucher_type": sinv.doctype,
			"voucher_no": sinv.name,
			"party_type": "Customer",
			"party": sinv.customer,
			"gl_balance": sinv.grand_total,
			"pl_balance": sinv.grand_total - 1,
			"account_currency": "INR",
			"gl_balance_in_account_currency": sinv.grand_total,
			"pl_balance_in_account_currency": sinv.grand_total,
		}
		self.assertEqual(expected, data[0])

		# account filter
		filters = frappe._dict({"company": self.company, "account": self.debit_to})
		columns, data = execute(filters=filters)
		self.assertEqual(len(data), 1)
		self.assertEqual(expected, data[0])

		filters = frappe._dict({"company": self.company, "account": self.creditors})
		columns, data = execute(filters=filters)
		self.assertEqual([], data)

		# voucher_no filter
		filters = frappe._dict({"company": self.company, "voucher_no": sinv.name})
		columns, data = execute(filters=filters)
		self.assertEqual(len(data), 1)
		self.assertEqual(expected, data[0])

		filters = frappe._dict({"company": self.company, "voucher_no": sinv.name + "-1"})
		columns, data = execute(filters=filters)
		self.assertEqual([], data)

		# date range filter
		filters = frappe._dict(
			{
				"company": self.company,
				"period_start_date": sinv.posting_date,
				"period_end_date": sinv.posting_date,
			}
		)
		columns, data = execute(filters=filters)
		self.assertEqual(len(data), 1)
		self.assertEqual(expected, data[0])

		filters = frappe._dict(
			{
				"company": self.company,
				"period_start_date": add_days(sinv.posting_date, -1),
				"period_end_date": add_days(sinv.posting_date, -1),
			}
		)
		columns, data = execute(filters=filters)
		self.assertEqual([], data)

	def test_rows_limited_to_permitted_parties(self):
		for customer in ("_Test Customer", "_Test Customer 1"):
			sinv = create_sales_invoice(
				company=self.company,
				customer=customer,
				debit_to=self.debit_to,
				expense_account=self.expense_account,
				cost_center=self.cost_center,
				income_account=self.income_account,
				warehouse=self.warehouse,
			)
			frappe.db.set_value(
				"Payment Ledger Entry",
				{"voucher_no": sinv.name, "delinked": 0},
				"amount",
				sinv.grand_total - 1,
			)

		user = "test_gl_pl_comparison@example.com"
		if not frappe.db.exists("User", user):
			# a welcome email is sent at once in tests, and sending it commits the invoices above
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "GLPL",
					"send_welcome_email": 0,
					"roles": [{"role": "Accounts User"}],
				}
			).insert()
		frappe.permissions.add_user_permission("Customer", "_Test Customer", user)

		frappe.set_user(user)
		try:
			data = execute(filters=frappe._dict({"company": self.company}))[1]
		finally:
			frappe.set_user("Administrator")

		self.assertEqual([row.party for row in data], ["_Test Customer"])

	def test_account_currencies_fetched_in_one_query(self):
		report = General_Payment_Ledger_Comparison(frappe._dict({"company": self.company}))
		balances = frappe._dict(
			gl_balance=10,
			pl_balance=0,
			gl_balance_in_account_currency=10,
			pl_balance_in_account_currency=0,
		)
		accounts = [self.debit_to, "_Test Payable USD - _TC"]
		report.diff = {(self.company, account, "", "", "", ""): balances for account in accounts}
		for account in accounts:
			frappe.clear_document_cache("Account", account)

		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
			report.generate_data()

		account_queries = [call for call in sql.call_args_list if "tabAccount" in str(call.args[0])]
		self.assertEqual(len(account_queries), 1)

		self.assertEqual(
			{row.account: row.account_currency for row in report.data},
			{self.debit_to: "INR", "_Test Payable USD - _TC": "USD"},
		)
