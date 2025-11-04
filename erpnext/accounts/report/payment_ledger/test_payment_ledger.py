import frappe
from frappe import qb
from frappe.tests import IntegrationTestCase

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.payment_ledger.payment_ledger import execute


class TestPaymentLedger(IntegrationTestCase):
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
