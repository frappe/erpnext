import frappe
from frappe.utils import getdate, today

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.report.item_wise_purchase_register.item_wise_purchase_register import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestItemWisePurchaseRegister(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.company = "_Test Company"
		self.supplier = "_Test Supplier"
		self.item = "_Test Item"

	def create_purchase_invoice(self, do_not_submit=False):
		pi = make_purchase_invoice(
			item=self.item,
			company=self.company,
			supplier=self.supplier,
			is_return=False,
			update_stock=False,
			do_not_save=1,
			rate=100,
			price_list_rate=100,
			qty=1,
		)

		pi = pi.save()
		if not do_not_submit:
			pi = pi.submit()
		return pi

	def test_basic_report_output(self):
		pi = self.create_purchase_invoice()

		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		report = execute(filters)

		self.assertEqual(len(report[1]), 1)

		expected_result = {
			"item_code": pi.items[0].item_code,
			"invoice": pi.name,
			"posting_date": getdate(),
			"supplier": pi.supplier,
			"credit_to": pi.credit_to,
			"company": self.company,
			"expense_account": pi.items[0].expense_account,
			"stock_qty": 1.0,
			"stock_uom": pi.items[0].stock_uom,
			"rate": 100.0,
			"amount": 100.0,
			"total_tax": 0,
			"total": 100.0,
			"currency": "INR",
		}

		report_output = {k: v for k, v in report[1][0].items() if k in expected_result}
		self.assertDictEqual(report_output, expected_result)

	def test_total_includes_other_charges(self):
		pi = make_purchase_invoice(
			item=self.item, company=self.company, supplier=self.supplier, rate=100, qty=1, do_not_save=1
		)
		for account, charge_type, rate, tax_amount in (
			("_Test Account VAT - _TC", "On Net Total", 18, 0),
			("_Test Account Shipping Charges - _TC", "Actual", 0, 10),
		):
			pi.append(
				"taxes",
				{
					"category": "Total",
					"add_deduct_tax": "Add",
					"charge_type": charge_type,
					"account_head": account,
					"cost_center": "_Test Cost Center - _TC",
					"description": account,
					"rate": rate,
					"tax_amount": tax_amount,
				},
			)
		pi.submit()

		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		row = execute(filters)[1][0]

		self.assertEqual(row["total_tax"], 18)
		self.assertEqual(row["total_other_charges"], 10)
		self.assertEqual(row["total"], pi.base_grand_total)

	def test_item_group_filter_includes_child_groups(self):
		pi = self.create_purchase_invoice()

		for item_group in ("All Item Groups", pi.items[0].item_group):
			filters = frappe._dict(
				{"from_date": today(), "to_date": today(), "company": self.company, "item_group": item_group}
			)
			self.assertEqual([row["invoice"] for row in execute(filters)[1]], [pi.name])
