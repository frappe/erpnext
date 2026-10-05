import frappe
from frappe import qb
from frappe.utils import add_days

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.general_and_payment_ledger_comparison.general_and_payment_ledger_comparison import (
	execute,
)
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestGeneralAndPaymentLedger(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.company = "_Test Company"
		self.debit_to = "Debtors - _TC"
		self.expense_account = "Cost of Goods Sold - _TC"
		self.cost_center = "Main - _TC"
		self.income_account = "Sales - _TC"
		self.warehouse = "Stores - _TC"
		self.creditors = "Creditors - _TC"
		self.cleanup()

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
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "GLPL", "roles": [{"role": "Accounts User"}]}
			).insert()
		frappe.permissions.add_user_permission("Customer", "_Test Customer", user)

		frappe.set_user(user)
		try:
			data = execute(filters=frappe._dict({"company": self.company}))[1]
		finally:
			frappe.set_user("Administrator")

		self.assertEqual([row.party for row in data], ["_Test Customer"])
