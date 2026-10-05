import frappe
from frappe import qb

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

	def test_rows_limited_to_permitted_parties(self):
		for customer in ("_Test Customer", "_Test Customer 1"):
			create_sales_invoice(
				company=self.company,
				customer=customer,
				debit_to=self.debit_to,
				expense_account=self.expense_account,
				cost_center=self.cost_center,
				income_account=self.income_account,
				warehouse=self.warehouse,
			)

		user = "test_payment_ledger@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "PL", "roles": [{"role": "Accounts User"}]}
			).insert()
		frappe.permissions.add_user_permission("Customer", "_Test Customer", user)

		frappe.set_user(user)
		try:
			data = execute(filters=frappe._dict({"company": self.company, "party_type": "Customer"}))[1]
		finally:
			frappe.set_user("Administrator")

		self.assertEqual({row.party for row in data if row.party}, {"_Test Customer"})
