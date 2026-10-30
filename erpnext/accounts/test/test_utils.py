import unittest

import frappe
from frappe.test_runner import make_test_objects

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.party import get_party_shipping_address
from erpnext.accounts.utils import (
	get_account_balances_coa,
	get_balance_on,
	get_currency_precision,
	get_future_stock_vouchers,
	get_voucherwise_gl_entries,
	get_zero_cutoff,
	sort_stock_vouchers_by_posting_date,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestUtils(ERPNextTestSuite):
	def test_balances_respect_finance_books(self):
		company = "_Test Company"
		frappe.db.set_value("Company", company, "default_finance_book", "")
		books = [
			frappe.get_doc(doctype="Finance Book", finance_book_name=name).insert().name
			for name in ("_Test Balance Default Book", "_Test Balance Alternative Book")
		]
		group = create_account(
			account_name="_Test Finance Book Balances",
			company=company,
			parent_account="Bank Accounts - _TC",
			is_group=1,
		)
		account = create_account(
			account_name="_Test Finance Book Balance Ledger", company=company, parent_account=group
		)
		for book, amount in ((None, 100), ("", 200), (books[0], 300), (books[1], 400)):
			journal = make_journal_entry(account, "Cash - _TC", amount, save=False)
			journal.finance_book = book
			journal.submit()
			frappe.db.set_value(
				"GL Entry",
				{"voucher_type": journal.doctype, "voucher_no": journal.name},
				"finance_book",
				book,
			)

		for default_book in ("", books[0]):
			frappe.db.set_value("Company", company, "default_finance_book", default_book)
			for include_default in (False, True):
				with self.subTest(default_book=default_book, include_default=include_default):
					balances = {
						row["value"]: row["balance"]
						for row in get_account_balances_coa(company, include_default)
					}
					expected = 600 if default_book and include_default else 300
					self.assertEqual(balances[account], expected)
					self.assertEqual(balances[group], expected)
					for selected in (None, "", *books):
						expected = 300
						if selected == books[0] or (default_book and include_default):
							expected += 300
						if selected == books[1]:
							expected += 400
						for name in (account, group):
							with self.subTest(account=name, selected=selected):
								self.assertEqual(
									get_balance_on(
										account=name,
										company=company,
										finance_book=selected,
										include_default_fb_balances=include_default,
									),
									expected,
								)
		self.assertEqual(get_balance_on(account=account), 300)

	def test_get_party_shipping_address(self):
		address = get_party_shipping_address("Customer", "_Test Customer 1")
		self.assertEqual(address, "_Test Billing Address 2 Title-Billing")

	def test_get_party_shipping_address2(self):
		address = get_party_shipping_address("Customer", "_Test Customer 2")
		self.assertEqual(address, "_Test Shipping Address 2 Title-Shipping")

	def test_get_voucher_wise_gl_entry(self):
		pr = make_purchase_receipt(
			item_code="_Test Item",
			posting_date="2021-02-01",
			rate=100,
			qty=1,
			warehouse="Stores - TCP1",
			company="_Test Company with perpetual inventory",
		)

		future_vouchers = get_future_stock_vouchers("2021-01-01", "00:00:00", for_items=["_Test Item"])

		voucher_type_and_no = ("Purchase Receipt", pr.name)
		self.assertTrue(
			voucher_type_and_no in future_vouchers,
			msg="get_future_stock_vouchers not returning correct value",
		)

		posting_date = "2021-01-01"
		gl_entries = get_voucherwise_gl_entries(future_vouchers, posting_date)
		self.assertTrue(
			voucher_type_and_no in gl_entries,
			msg="get_voucherwise_gl_entries not returning expected GLes",
		)

	def test_stock_voucher_sorting(self):
		vouchers = []

		item = make_item().name

		stock_entry = {"item": item, "to_warehouse": "_Test Warehouse - _TC", "qty": 1, "rate": 10}

		se1 = make_stock_entry(posting_date="2022-01-01", **stock_entry)
		se3 = make_stock_entry(posting_date="2022-03-01", **stock_entry)
		se2 = make_stock_entry(posting_date="2022-02-01", **stock_entry)

		for doc in (se1, se2, se3):
			vouchers.append((doc.doctype, doc.name))

		vouchers.append(("Stock Entry", "Wat"))

		sorted_vouchers = sort_stock_vouchers_by_posting_date(list(reversed(vouchers)))
		self.assertEqual(sorted_vouchers, vouchers)

	def test_update_reference_in_payment_entry(self):
		item = make_item().name

		purchase_invoice = make_purchase_invoice(
			item=item, supplier="_Test Supplier USD", currency="USD", conversion_rate=82.32, do_not_submit=1
		)
		purchase_invoice.credit_to = "_Test Payable USD - _TC"
		purchase_invoice.submit()

		payment_entry = get_payment_entry(purchase_invoice.doctype, purchase_invoice.name)
		payment_entry.target_exchange_rate = 82.32
		payment_entry.set_amounts()
		payment_entry.paid_amount = 15725
		payment_entry.deductions = []
		payment_entry.save()

		# below is the difference between base_paid_amount and base_received_amount (exchange gain)
		self.assertEqual(payment_entry.deductions[0].amount, -4855.0)

		payment_entry.target_exchange_rate = 62.9
		payment_entry.save()

		# after changing the exchange rate, there is no exchange gain / loss
		self.assertEqual(payment_entry.deductions, [])

		payment_entry.references = []
		self.assertEqual(payment_entry.difference_amount, 0.0)
		payment_entry.submit()

		payment_reconciliation = frappe.new_doc("Payment Reconciliation")
		payment_reconciliation.company = payment_entry.company
		payment_reconciliation.party_type = "Supplier"
		payment_reconciliation.party = purchase_invoice.supplier
		payment_reconciliation.receivable_payable_account = payment_entry.paid_to
		payment_reconciliation.get_unreconciled_entries()
		payment_reconciliation.allocate_entries(
			{
				"payments": [d.__dict__ for d in payment_reconciliation.payments],
				"invoices": [d.__dict__ for d in payment_reconciliation.invoices],
			}
		)
		for d in payment_reconciliation.invoices:
			# Reset invoice outstanding_amount because allocate_entries will zero this value out.
			d.outstanding_amount = d.amount
		for d in payment_reconciliation.allocation:
			d.difference_account = "Exchange Gain/Loss - _TC"
		payment_reconciliation.reconcile()

		payment_entry.load_from_db()
		self.assertEqual(len(payment_entry.references), 1)
		self.assertEqual(payment_entry.difference_amount, 0)

	def test_naming_series_variable_parsing(self):
		"""
		Tests parsing utility used by Naming Series Variable hook for FY
		"""
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter
		from frappe.utils import nowdate

		from erpnext.accounts.utils import get_fiscal_year
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		# Configure Supplier Naming in Buying Settings
		frappe.db.set_default("supp_master_name", "Auto Name")

		# Configure Autoname in Supplier DocType
		make_property_setter("Supplier", None, "naming_rule", "Expression", "Data", for_doctype="Doctype")
		make_property_setter("Supplier", None, "autoname", "SUP-.FY.-.#####", "Data", for_doctype="Doctype")

		fiscal_year = get_fiscal_year(nowdate())[0]

		# Create Supplier
		supplier = create_supplier()

		# Check Naming Series in generated Supplier ID
		doc_name = supplier.name.split("-")
		self.assertEqual(len(doc_name), 3)
		self.assertSequenceEqual(doc_name[0:2], ("SUP", fiscal_year))
		frappe.db.set_default("supp_master_name", "Supplier Name")

	def test_get_zero_cutoff(self):
		self.assertEqual(get_zero_cutoff(None), 0.005)
		self.assertEqual(get_zero_cutoff("EUR"), 0.005)
		self.assertEqual(get_zero_cutoff("BHD"), 0.0005)

	def test_get_currency_precision_respects_zero_and_fallback(self):
		currency_precision = frappe.db.get_default("currency_precision")
		number_format = frappe.db.get_default("number_format")

		try:
			frappe.db.set_default("number_format", "#,###.##")
			frappe.db.set_default("currency_precision", "0")
			self.assertEqual(get_currency_precision(), 0)

			frappe.db.set_default("currency_precision", "")
			self.assertEqual(get_currency_precision(), 2)
		finally:
			frappe.db.set_default("currency_precision", currency_precision or "")
			frappe.db.set_default("number_format", number_format or "#,###.##")
