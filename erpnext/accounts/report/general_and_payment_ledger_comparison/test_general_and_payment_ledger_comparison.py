import frappe
from frappe import qb
from frappe.utils import add_days

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
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
			"against_voucher_type": sinv.doctype,
			"against_voucher_no": sinv.name,
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

	def test_payment_applied_to_another_invoice_in_payment_ledger(self):
		invoices = [
			create_sales_invoice(
				company=self.company,
				debit_to=self.debit_to,
				expense_account=self.expense_account,
				cost_center=self.cost_center,
				income_account=self.income_account,
				warehouse=self.warehouse,
			)
			for _i in range(2)
		]
		payment = get_payment_entry("Sales Invoice", invoices[0].name)
		# 20 stays unallocated: it has no against voucher in GL and must not be reported
		payment.paid_amount = payment.received_amount = 60
		payment.references[0].allocated_amount = 40
		payment.submit()
		frappe.db.set_value(
			"Payment Ledger Entry",
			{"voucher_no": payment.name, "against_voucher_no": invoices[0].name, "delinked": 0},
			"against_voucher_no",
			invoices[1].name,
		)

		data = execute(filters=frappe._dict({"company": self.company}))[1]

		# the row re-pointed to another invoice is counted under the unallocated amount
		against = {(row.voucher_no, row.against_voucher_no): (row.gl_balance, row.pl_balance) for row in data}
		self.assertEqual(
			against,
			{
				(payment.name, invoices[0].name): (-40, None),
				(payment.name, payment.name): (-20, -60),
			},
		)

	def test_payment_reconciled_to_invoice_is_not_reported(self):
		invoice = create_sales_invoice(
			company=self.company,
			debit_to=self.debit_to,
			expense_account=self.expense_account,
			cost_center=self.cost_center,
			income_account=self.income_account,
			warehouse=self.warehouse,
		)
		payment = get_payment_entry("Sales Invoice", invoice.name)
		payment.paid_amount = payment.received_amount = 60
		payment.references = []
		payment.submit()

		reconciliation = frappe.new_doc("Payment Reconciliation")
		reconciliation.update(
			{
				"company": self.company,
				"party_type": "Customer",
				"party": invoice.customer,
				"receivable_payable_account": self.debit_to,
			}
		)
		reconciliation.get_unreconciled_entries()
		reconciliation.allocate_entries(
			frappe._dict(
				invoices=[
					row.as_dict() for row in reconciliation.invoices if row.invoice_number == invoice.name
				],
				payments=[
					row.as_dict() for row in reconciliation.payments if row.reference_name == payment.name
				],
			)
		)
		reconciliation.reconcile()

		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "outstanding_amount"), 40)
		self.assertEqual(execute(filters=frappe._dict({"company": self.company}))[1], [])
