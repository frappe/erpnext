import unittest

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, flt, getdate, today

from erpnext import get_default_cost_center
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.accounts_payable.accounts_payable import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order


class TestAccountsReceivable(AccountsTestMixin, FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()
		self.create_supplier(currency="USD", supplier_name="Test Supplier2")
		self.create_usd_payable_account()

	def tearDown(self):
		frappe.db.rollback()

	def test_accounts_payable_for_foreign_currency_supplier(self):
		pi = self.create_purchase_invoice(do_not_submit=True)
		pi.currency = "USD"
		pi.conversion_rate = 80
		pi.credit_to = self.creditors_usd
		pi = pi.save().submit()

		filters = {
			"company": self.company,
			"party_type": "Supplier",
			"party": [self.supplier],
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
		}

		data = execute(filters)
		self.assertEqual(data[1][0].get("outstanding"), 300)
		self.assertEqual(data[1][0].get("currency"), "USD")

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
