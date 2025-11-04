import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.item_wise_sales_register.item_wise_sales_register import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestItemWiseSalesRegister(AccountsTestMixin, IntegrationTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()

	def tearDown(self):
		frappe.db.rollback()

	def create_sales_invoice(self, do_not_submit=False):
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
			price_list_rate=100,
			do_not_save=1,
		)
		si = si.save()
		if not do_not_submit:
			si = si.submit()
		return si

	def test_basic_report_output(self):
		si = self.create_sales_invoice()

		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		report = execute(filters)

		self.assertEqual(len(report[1]), 1)

		expected_result = {
			"item_code": si.items[0].item_code,
			"invoice": si.name,
			"posting_date": getdate(),
			"customer": si.customer,
			"debit_to": si.debit_to,
			"company": self.company,
			"income_account": si.items[0].income_account,
			"stock_qty": 1.0,
			"stock_uom": si.items[0].stock_uom,
			"rate": 100.0,
			"amount": 100.0,
			"total_tax": 0,
			"total_other_charges": 0,
			"total": 100.0,
			"currency": "INR",
		}

		report_output = {k: v for k, v in report[1][0].items() if k in expected_result}
		self.assertDictEqual(report_output, expected_result)
