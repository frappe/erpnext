import frappe
from frappe import qb
from frappe.core.doctype.user_permission.test_user_permission import create_user

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.payment_ledger.payment_ledger import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestPaymentLedger(ERPNextTestSuite):
	def setUp(self):
		self.company = "_Test Company"
		self.cost_center = "Main - _TC"
		self.warehouse = "Stores - _TC"
		self.income_account = "Sales - _TC"
		self.expense_account = "Cost of Goods Sold - _TC"
		self.debit_to = "Debtors - _TC"

	def test_unpaid_invoice_outstanding(self):
		sinv = create_sales_invoice(
			company=self.company,
			debit_to=self.debit_to,
			expense_account=self.expense_account,
			cost_center=self.cost_center,
			income_account=self.income_account,
			warehouse=self.warehouse,
		)
		get_payment_entry(sinv.doctype, sinv.name).save().submit()

		filters = frappe._dict({"company": self.company})
		columns, data = execute(filters=filters)
		outstanding = [x for x in data if x.get("against_voucher_no") == "Outstanding:"]
		self.assertEqual(outstanding[0].get("amount"), 0)

	def test_user_permission_on_company(self):
		own = create_sales_invoice(
			company=self.company,
			debit_to=self.debit_to,
			expense_account=self.expense_account,
			cost_center=self.cost_center,
			income_account=self.income_account,
			warehouse=self.warehouse,
		)
		other = create_sales_invoice(
			company="_Test Company 1",
			debit_to="Debtors - _TC1",
			expense_account="Cost of Goods Sold - _TC1",
			cost_center="Main - _TC1",
			income_account="Sales - _TC1",
			warehouse="Stores - _TC1",
			currency="USD",
		)
		user = create_user("test_payment_ledger_user@example.com", "Accounts User")
		frappe.permissions.add_user_permission("Company", self.company, user.name)

		with self.set_user(user.name):
			columns, data = execute(filters=frappe._dict())
		voucher_nos = {x.get("voucher_no") for x in data}
		self.assertIn(own.name, voucher_nos)
		self.assertNotIn(other.name, voucher_nos)

	def test_user_permission_on_party(self):
		own = create_sales_invoice(
			company=self.company,
			debit_to=self.debit_to,
			expense_account=self.expense_account,
			cost_center=self.cost_center,
			income_account=self.income_account,
			warehouse=self.warehouse,
		)
		other = create_sales_invoice(
			company=self.company,
			customer="_Test Customer 1",
			debit_to=self.debit_to,
			expense_account=self.expense_account,
			cost_center=self.cost_center,
			income_account=self.income_account,
			warehouse=self.warehouse,
		)
		partyless = make_journal_entry(self.debit_to, self.income_account, 100, save=False)
		partyless.party_not_required = 1
		partyless.submit()
		no_party = make_journal_entry(self.debit_to, self.income_account, 100, save=False)
		no_party.party_not_required = 1
		no_party.accounts[0].party_type = "Customer"
		no_party.submit()
		user = create_user("test_payment_ledger_party_user@example.com", "Accounts User")
		frappe.permissions.add_user_permission("Customer", own.customer, user.name)

		with self.set_user(user.name):
			columns, data = execute(filters=frappe._dict())
		voucher_nos = {x.get("voucher_no") for x in data}
		self.assertIn(own.name, voucher_nos)
		self.assertNotIn(other.name, voucher_nos)
		self.assertIn(partyless.name, voucher_nos)
		self.assertIn(no_party.name, voucher_nos)

		scoped = create_user("test_payment_ledger_scoped_user@example.com", "Accounts User")
		frappe.permissions.add_user_permission(
			"Customer", own.customer, scoped.name, applicable_for="Payment Ledger Entry"
		)

		with self.set_user(scoped.name):
			columns, data = execute(filters=frappe._dict())
		voucher_nos = {x.get("voucher_no") for x in data}
		self.assertIn(own.name, voucher_nos)
		self.assertNotIn(other.name, voucher_nos)
