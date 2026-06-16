# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils import add_months, flt, today

from erpnext.accounts.report.purchase_register.purchase_register import execute
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestPurchaseRegister(ERPNextTestSuite):
	def test_purchase_register(self):
		filters = frappe._dict(company="_Test Company 6", from_date=add_months(today(), -1), to_date=today())

		pi = make_purchase_invoice()

		report_results = execute(filters)
		first_row = frappe._dict(report_results[1][0])
		self.assertEqual(first_row.voucher_type, "Purchase Invoice")
		self.assertEqual(first_row.voucher_no, pi.name)
		self.assertEqual(first_row.payable_account, "Creditors - _TC6")
		self.assertEqual(first_row.net_total, 1000)
		self.assertEqual(first_row.total_tax, 100)
		self.assertEqual(first_row.grand_total, 1100)

	def test_expense_account_columns_sorted_case_insensitively(self):
		# The dynamic expense-account columns must follow MariaDB's case-insensitive collation order and
		# be identical on both engines. frappe drops ORDER BY for distinct queries on postgres, so the
		# report sorts in python with casefold; plain sorted() would be case-sensitive ("ZZZ" < "aaa").
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice

		company = "_Test Company"
		lower = create_account(
			account_name="aaa Test Expense", parent_account="Expenses - _TC", company=company
		)
		upper = create_account(
			account_name="ZZZ Test Expense", parent_account="Expenses - _TC", company=company
		)
		for account in (upper, lower):  # submit in non-casefold order
			make_purchase_invoice(company=company, expense_account=account)

		filters = frappe._dict(company=company, from_date=add_months(today(), -1), to_date=today())
		columns = execute(filters)[0]
		labels = [col["label"] for col in columns if col.get("label") in (lower, upper)]

		self.assertEqual(labels, sorted([lower, upper], key=str.casefold))

	def test_purchase_register_ignores_tax_rows_from_other_doctype(self):
		filters = frappe._dict(company="_Test Company 6", from_date=add_months(today(), -1), to_date=today())

		pi = make_purchase_invoice()

		# Real workflow setup: create a Purchase Receipt tax row in the same shared child table.
		pr = make_purchase_receipt(
			company="_Test Company 6",
			supplier="_Test Supplier",
			item="_Test Item",
			warehouse="_Test Warehouse - _TC6",
			cost_center="_Test Cost Center - _TC6",
			do_not_save=1,
			do_not_submit=1,
			qty=1,
			rate=1000,
		)
		pr.append(
			"taxes",
			{
				"account_head": "GST - _TC6",
				"cost_center": "_Test Cost Center - _TC6",
				"add_deduct_tax": "Add",
				"category": "Valuation and Total",
				"charge_type": "Actual",
				"description": "PR Tax",
				"tax_amount": 100.0,
				"rate": 100,
			},
		)
		pr.insert()
		pr.submit()

		# Mimic custom naming collision across doctypes (same parent value in shared child table).
		frappe.rename_doc("Purchase Receipt", pr.name, pi.name, force=True)

		report_results = execute(filters)
		first_row = frappe._dict(report_results[1][0])

		self.assertEqual(first_row.voucher_no, pi.name)
		self.assertEqual(first_row.total_tax, 100)
		self.assertEqual(first_row.grand_total, 1100)

	def test_purchase_currency_conversion(self):
		usd_creditors = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "USD Creditors",
				"parent_account": "Accounts Payable - _TC",
				"company": "_Test Company",
				"account_type": "Payable",
				"root_type": "Liability",
				"report_type": "Balance Sheet",
				"account_currency": "USD",
			}
		).insert()
		foreign_invoice = make_purchase_invoice()
		foreign_invoice.db_set("currency", "USD")
		foreign_invoice.db_set("conversion_rate", 80)
		foreign_invoice.db_set("credit_to", usd_creditors.name)
		foreign_invoice.db_set("outstanding_amount", 100.236)
		local_invoice = make_purchase_invoice()
		local_invoice.db_set("currency", "INR")
		local_invoice.db_set("conversion_rate", 1)
		local_invoice.db_set("outstanding_amount", 200.456)
		columns, data, *_ = execute(frappe._dict({"company": foreign_invoice.company}))
		outstanding_precision = 2

		data_by_name = {x.get("voucher_no"): x.get("outstanding_amount") for x in data}
		self.assertEqual(data_by_name.get(foreign_invoice.name), flt((100.236 * 80), outstanding_precision))
		self.assertEqual(data_by_name.get(local_invoice.name), flt(200.456, outstanding_precision))

	def test_purchase_register_ledger_view(self):
		filters = frappe._dict(
			company="_Test Company 6",
			from_date=add_months(today(), -1),
			to_date=today(),
			include_payments=True,
			supplier="_Test Supplier",
		)

		make_purchase_invoice()
		pe = make_payment_entry()

		report_results = execute(filters)
		first_row = frappe._dict(report_results[1][2])
		self.assertEqual(first_row.voucher_type, "Payment Entry")
		self.assertEqual(first_row.voucher_no, pe.name)
		self.assertEqual(first_row.payable_account, "Creditors - _TC6")
		self.assertEqual(first_row.debit, 0)
		self.assertEqual(first_row.credit, 600)
		self.assertEqual(first_row.balance, 500)


def make_purchase_invoice():
	from erpnext.accounts.doctype.account.test_account import create_account
	from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	create_account(
		account_name="GST",
		account_type="Tax",
		parent_account="Duties and Taxes - _TC6",
		company="_Test Company 6",
		account_currency="INR",
	)
	create_warehouse(warehouse_name="_Test Warehouse - _TC6", company="_Test Company 6")
	create_cost_center(cost_center_name="_Test Cost Center", company="_Test Company 6")
	pi = create_purchase_invoice_with_taxes()
	pi.submit()
	return pi


def create_purchase_invoice_with_taxes():
	return frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"posting_date": today(),
			"supplier": "_Test Supplier",
			"company": "_Test Company 6",
			"cost_center": "_Test Cost Center - _TC6",
			"taxes_and_charges": "",
			"currency": "INR",
			"credit_to": "Creditors - _TC6",
			"items": [
				{
					"doctype": "Purchase Invoice Item",
					"cost_center": "_Test Cost Center - _TC6",
					"item_code": "_Test Item",
					"qty": 1,
					"rate": 1000,
					"expense_account": "Stock Received But Not Billed - _TC6",
				}
			],
			"taxes": [
				{
					"account_head": "GST - _TC6",
					"cost_center": "_Test Cost Center - _TC6",
					"add_deduct_tax": "Add",
					"category": "Valuation and Total",
					"charge_type": "Actual",
					"description": "Shipping Charges",
					"doctype": "Purchase Taxes and Charges",
					"parentfield": "taxes",
					"rate": 100,
					"tax_amount": 100.0,
				}
			],
		}
	)


def make_payment_entry():
	frappe.set_user("Administrator")
	from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

	return create_payment_entry(
		company="_Test Company 6",
		party_type="Supplier",
		party="_Test Supplier",
		payment_type="Pay",
		paid_from="Cash - _TC6",
		paid_to="Creditors - _TC6",
		paid_amount=600,
		save=1,
		submit=1,
	)
