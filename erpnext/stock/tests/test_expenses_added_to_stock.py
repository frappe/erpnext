# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company with perpetual inventory"
WAREHOUSE = "Stores - TCP1"


class TestExpensesAddedToStock(ERPNextTestSuite):
	def setUp(self):
		self.eats_account = create_account(
			account_name="Expenses Added To Stock",
			parent_account="Expenses - TCP1",
			company=COMPANY,
		)
		self.eats_contra_account = create_account(
			account_name="Expenses Added To Stock Contra",
			parent_account="Expenses - TCP1",
			company=COMPANY,
		)
		self.purchase_expense_account = create_account(
			account_name="Test Purchase Expense EATS",
			parent_account="Expenses - TCP1",
			company=COMPANY,
		)
		self.purchase_expense_contra_account = create_account(
			account_name="Test Purchase Expense Contra EATS",
			parent_account="Expenses - TCP1",
			company=COMPANY,
		)
		frappe.db.set_value(
			"Company",
			COMPANY,
			{
				"expenses_added_to_stock_account": self.eats_account,
				"expenses_added_to_stock_contra_account": self.eats_contra_account,
				"purchase_expense_account": self.purchase_expense_account,
				"purchase_expense_contra_account": self.purchase_expense_contra_account,
			},
		)
		frappe.db.set_single_value("Accounts Settings", "book_stock_expense_gl_entries", 1)
		self.item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

	def get_gl_balances(self, voucher_type, voucher_no):
		entries = frappe.get_all(
			"GL Entry",
			filters={
				"voucher_type": voucher_type,
				"voucher_no": voucher_no,
				"is_cancelled": 0,
				"account": ("in", [self.eats_account, self.eats_contra_account]),
			},
			fields=["account", "debit", "credit"],
		)

		balances = frappe._dict({self.eats_account: 0.0, self.eats_contra_account: 0.0})
		debits = frappe._dict({self.eats_account: 0.0, self.eats_contra_account: 0.0})
		credits = frappe._dict({self.eats_account: 0.0, self.eats_contra_account: 0.0})
		for entry in entries:
			balances[entry.account] += entry.debit - entry.credit
			debits[entry.account] += entry.debit
			credits[entry.account] += entry.credit

		return balances, debits, credits

	def test_material_receipt_books_expenses_added_to_stock(self):
		se = make_stock_entry(item_code=self.item, to_warehouse=WAREHOUSE, qty=10, rate=100, company=COMPANY)

		_balances, debits, credits = self.get_gl_balances("Stock Entry", se.name)
		self.assertEqual(debits[self.eats_account], 1000)
		self.assertEqual(credits[self.eats_contra_account], 1000)

	def test_material_issue_books_reverse_pair(self):
		make_stock_entry(item_code=self.item, to_warehouse=WAREHOUSE, qty=10, rate=100, company=COMPANY)
		se = make_stock_entry(item_code=self.item, from_warehouse=WAREHOUSE, qty=5, company=COMPANY)

		_balances, debits, credits = self.get_gl_balances("Stock Entry", se.name)
		self.assertEqual(credits[self.eats_account], 500)
		self.assertEqual(debits[self.eats_contra_account], 500)

	def test_material_transfer_books_nothing(self):
		make_stock_entry(item_code=self.item, to_warehouse=WAREHOUSE, qty=10, rate=100, company=COMPANY)
		se = make_stock_entry(
			item_code=self.item,
			from_warehouse=WAREHOUSE,
			to_warehouse="Finished Goods - TCP1",
			qty=5,
			company=COMPANY,
		)

		_balances, debits, credits = self.get_gl_balances("Stock Entry", se.name)
		self.assertEqual(debits[self.eats_account], 0)
		self.assertEqual(credits[self.eats_account], 0)

	def test_stock_reconciliation_books_pair(self):
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		make_stock_entry(item_code=self.item, to_warehouse=WAREHOUSE, qty=10, rate=100, company=COMPANY)
		sr = create_stock_reconciliation(
			item_code=self.item, warehouse=WAREHOUSE, qty=15, rate=100, company=COMPANY
		)

		_balances, debits, credits = self.get_gl_balances("Stock Reconciliation", sr.name)
		self.assertEqual(debits[self.eats_account], 500)
		self.assertEqual(credits[self.eats_contra_account], 500)

	def test_landed_cost_voucher_books_pair(self):
		from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import (
			create_landed_cost_voucher,
		)
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		pr = make_purchase_receipt(
			company=COMPANY, warehouse=WAREHOUSE, item_code=self.item, qty=10, rate=100
		)

		_balances, debits, credits = self.get_gl_balances("Purchase Receipt", pr.name)
		self.assertEqual(debits[self.eats_account], 0)

		create_landed_cost_voucher("Purchase Receipt", pr.name, COMPANY, charges=200)

		_balances, debits, credits = self.get_gl_balances("Purchase Receipt", pr.name)
		self.assertEqual(debits[self.eats_account], 200)
		self.assertEqual(credits[self.eats_contra_account], 200)

	def test_no_entries_when_feature_disabled(self):
		frappe.db.set_single_value("Accounts Settings", "book_stock_expense_gl_entries", 0)

		se = make_stock_entry(item_code=self.item, to_warehouse=WAREHOUSE, qty=10, rate=100, company=COMPANY)

		_balances, debits, credits = self.get_gl_balances("Stock Entry", se.name)
		self.assertEqual(debits[self.eats_account], 0)
		self.assertEqual(credits[self.eats_contra_account], 0)

	def test_unconfigured_company_skips_booking(self):
		frappe.db.set_value(
			"Company",
			COMPANY,
			{
				"expenses_added_to_stock_account": None,
				"expenses_added_to_stock_contra_account": None,
			},
		)

		se = make_stock_entry(item_code=self.item, to_warehouse=WAREHOUSE, qty=10, rate=100, company=COMPANY)

		_balances, debits, credits = self.get_gl_balances("Stock Entry", se.name)
		self.assertEqual(debits[self.eats_account], 0)
		self.assertEqual(credits[self.eats_contra_account], 0)

	def test_missing_contra_account_raises_when_feature_enabled(self):
		frappe.db.set_value("Company", COMPANY, "expenses_added_to_stock_contra_account", None)

		self.assertRaises(
			frappe.ValidationError,
			make_stock_entry,
			item_code=self.item,
			to_warehouse=WAREHOUSE,
			qty=10,
			rate=100,
			company=COMPANY,
		)
