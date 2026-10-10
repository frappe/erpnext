import frappe
from frappe import qb
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.payment_ledger.payment_ledger import execute


class TestPaymentLedger(FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.cleanup()

	def cleanup(self):
		doctypes = []
		doctypes.append(qb.DocType("GL Entry"))
		doctypes.append(qb.DocType("Payment Ledger Entry"))
		doctypes.append(qb.DocType("Sales Invoice"))
		doctypes.append(qb.DocType("Payment Entry"))

		for doctype in doctypes:
			qb.from_(doctype).delete().where(doctype.company == self.company).run()

	def create_company(self):
		name = "Test Payment Ledger"
		company = None
		if frappe.db.exists("Company", name):
			company = frappe.get_doc("Company", name)
		else:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": name,
					"country": "India",
					"default_currency": "INR",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
				}
			)
			company = company.save()
		self.company = company.name
		self.cost_center = company.cost_center
		self.warehouse = "All Warehouses" + " - " + company.abbr
		self.income_account = company.default_income_account
		self.expense_account = company.default_expense_account
		self.debit_to = company.default_receivable_account

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
		other = create_sales_invoice()

		user = create_user("test_payment_ledger_user@example.com", "Accounts User")
		add_user_permission("Company", self.company, user.name)

		with self.set_user(user.name):
			columns, data = execute(filters=frappe._dict())

		vouchers = [x.get("voucher_no") for x in data]
		self.assertIn(own.name, vouchers)
		self.assertNotIn(other.name, vouchers)

	def test_user_permission_on_party(self):
		args = dict(
			company=self.company,
			debit_to=self.debit_to,
			expense_account=self.expense_account,
			cost_center=self.cost_center,
			income_account=self.income_account,
			warehouse=self.warehouse,
		)
		own = create_sales_invoice(customer="_Test Customer", **args)
		other = create_sales_invoice(customer="_Test Customer 1", **args)
		partyless = make_journal_entry(
			self.debit_to,
			self.income_account,
			100,
			cost_center=self.cost_center,
			save=False,
			company=self.company,
		)
		partyless.party_not_required = 1
		partyless.submit()
		no_party = make_journal_entry(
			self.debit_to,
			self.income_account,
			100,
			cost_center=self.cost_center,
			save=False,
			company=self.company,
		)
		no_party.party_not_required = 1
		no_party.accounts[0].party_type = "Customer"
		no_party.submit()

		user = create_user("test_payment_ledger_party_user@example.com", "Accounts User")
		add_user_permission("Customer", "_Test Customer", user.name)

		with self.set_user(user.name):
			columns, data = execute(filters=frappe._dict())

		vouchers = [x.get("voucher_no") for x in data]
		self.assertIn(own.name, vouchers)
		self.assertNotIn(other.name, vouchers)
		self.assertIn(partyless.name, vouchers)
		self.assertIn(no_party.name, vouchers)

		scoped = create_user("test_payment_ledger_scoped_user@example.com", "Accounts User")
		add_user_permission("Customer", "_Test Customer", scoped.name, applicable_for="Payment Ledger Entry")

		with self.set_user(scoped.name):
			columns, data = execute(filters=frappe._dict())

		vouchers = [x.get("voucher_no") for x in data]
		self.assertIn(own.name, vouchers)
		self.assertNotIn(other.name, vouchers)
