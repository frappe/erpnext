import unittest

import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.general_and_payment_ledger_comparison.general_and_payment_ledger_comparison import (
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
		ple = frappe.db.get_all(
			"Payment Ledger Entry", filters={"voucher_no": sinv.name, "delinked": 0}
		)[0]
		frappe.db.set_value("Payment Ledger Entry", ple.name, "amount", sinv.grand_total - 1)

		filters = frappe._dict({"company": self.company})
		columns, data = execute(filters=filters)
		self.assertEqual(len(data), 1)

		expected = {
			"voucher_no": sinv.name,
			"party": sinv.customer,
			"gl_balance": sinv.grand_total,
			"pl_balance": sinv.grand_total - 1,
		}
		self.assertEqual(expected, data[0])
