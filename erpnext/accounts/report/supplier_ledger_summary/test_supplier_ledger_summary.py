import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.report.supplier_ledger_summary.supplier_ledger_summary import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestSupplierLedgerSummary(AccountsTestMixin, IntegrationTestCase):
	def setUp(self):
		self.create_company()
		self.create_supplier()
		self.create_item()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def create_purchase_invoice(self, do_not_submit=False):
		frappe.set_user("Administrator")
		pi = make_purchase_invoice(
			item=self.item,
			company=self.company,
			supplier=self.supplier,
			is_return=False,
			update_stock=False,
			posting_date=frappe.utils.datetime.date(2021, 5, 1),
			do_not_save=1,
			rate=300,
			price_list_rate=300,
			qty=1,
		)

		pi = pi.save()
		if not do_not_submit:
			pi = pi.submit()
		return pi

	def test_basic_supplier_ledger_summary(self):
		self.create_purchase_invoice()

		filters = {"company": self.company, "from_date": today(), "to_date": today()}

		expected = {
			"party": "_Test Supplier",
			"party_name": "_Test Supplier",
			"opening_balance": 0,
			"invoiced_amount": 300.0,
			"paid_amount": 0,
			"return_amount": 0,
			"closing_balance": 300.0,
			"currency": "INR",
			"supplier_name": "_Test Supplier",
		}

		report_output = execute(filters)[1]
		self.assertEqual(len(report_output), 1)
		for field in expected:
			with self.subTest(field=field):
				self.assertEqual(report_output[0].get(field), expected.get(field))

	def test_supplier_ledger_summary_with_filters(self):
		self.create_purchase_invoice()

		supplier_group = frappe.db.get_value("Supplier", self.supplier, "supplier_group")

		filters = {
			"company": self.company,
			"from_date": today(),
			"to_date": today(),
			"supplier_group": supplier_group,
		}

		expected = {
			"party": "_Test Supplier",
			"party_name": "_Test Supplier",
			"opening_balance": 0,
			"invoiced_amount": 300.0,
			"paid_amount": 0,
			"return_amount": 0,
			"closing_balance": 300.0,
			"currency": "INR",
			"supplier_name": "_Test Supplier",
		}

		report_output = execute(filters)[1]
		self.assertEqual(len(report_output), 1)
		for field in expected:
			with self.subTest(field=field):
				self.assertEqual(report_output[0].get(field), expected.get(field))
