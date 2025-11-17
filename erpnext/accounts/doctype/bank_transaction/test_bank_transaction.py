# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import frappe
from frappe import utils
from frappe.model.docstatus import DocStatus
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import (
	get_linked_payments,
	reconcile_vouchers,
)
from erpnext.accounts.doctype.mode_of_payment.test_mode_of_payment import (
	set_default_account_for_mode_of_payment,
)
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.utils import if_lending_app_installed

test_dependencies = ["Item", "Cost Center"]


class TestBankTransaction(FrappeTestCase):
	def setUp(self):
		for dt in [
			"Bank Transaction",
			"Payment Entry",
			"Payment Entry Reference",
			"POS Profile",
		]:
			frappe.db.delete(dt)
		clear_loan_transactions()
		make_pos_profile()

		# generate and use a uniq hash identifier for 'Bank Account' and it's linked GL 'Account' to avoid validation error
		uniq_identifier = frappe.generate_hash(length=10)
		gl_account = create_gl_account("_Test Bank " + uniq_identifier)
		bank_account = create_bank_account(
			gl_account=gl_account, bank_account_name="Checking Account " + uniq_identifier
		)
		frappe.db.set_value(
			"Company",
			"_Test Company",
			"stock_received_but_not_billed",
			f"Stock Received But Not Billed - _TC",
		)
		add_transactions(bank_account=bank_account)
		add_vouchers(gl_account=gl_account)

	# This test checks if ERPNext is able to provide a linked payment for a bank transaction based on the amount of the bank transaction.
	def test_linked_payments(self):
		bank_transaction = frappe.get_doc(
			"Bank Transaction",
			dict(description="Re 95282925234 FE/000002917 AT171513000281183046 Conrad Electronic"),
		)
		linked_payments = get_linked_payments(
			bank_transaction.name,
			["payment_entry", "exact_match"],
			from_date=bank_transaction.date,
			to_date=utils.today(),
		)
		self.assertTrue(linked_payments[0]["party"] == "Conrad Electronic")

	# This test validates a simple reconciliation leading to the clearance of the bank transaction and the payment
	def test_reconcile(self):
		bank_transaction = frappe.get_doc(
			"Bank Transaction",
			dict(description="1512567 BG/000003025 OPSKATTUZWXXX AT776000000098709849 Herr G"),
		)
		payment = frappe.get_doc("Payment Entry", dict(party="Mr G", paid_amount=1700))
		vouchers = json.dumps(
			[
				{
					"payment_doctype": "Payment Entry",
					"payment_name": payment.name,
					"amount": bank_transaction.unallocated_amount,
				}
			]
		)
		reconcile_vouchers(bank_transaction.name, vouchers)

		unallocated_amount = frappe.db.get_value(
			"Bank Transaction", bank_transaction.name, "unallocated_amount"
		)
		self.assertTrue(unallocated_amount == 0)

		clearance_date = frappe.db.get_value("Payment Entry", payment.name, "clearance_date")
		self.assertTrue(clearance_date is not None)

		bank_transaction.reload()
		bank_transaction.cancel()

		clearance_date = frappe.db.get_value("Payment Entry", payment.name, "clearance_date")
		self.assertFalse(clearance_date)

	def test_cancel_voucher(self):
		bank_transaction = frappe.get_doc(
			"Bank Transaction",
			dict(description="1512567 BG/000003025 OPSKATTUZWXXX AT776000000098709849 Herr G"),
		)
		payment = frappe.get_doc("Payment Entry", dict(party="Mr G", paid_amount=1700))
		vouchers = json.dumps(
			[
				{
					"payment_doctype": "Payment Entry",
					"payment_name": payment.name,
					"amount": bank_transaction.unallocated_amount,
				}
			]
		)
		reconcile_vouchers(bank_transaction.name, vouchers)
		payment.reload()
		payment.cancel()
		bank_transaction.reload()
		self.assertEqual(bank_transaction.docstatus, DocStatus.submitted())
		self.assertEqual(bank_transaction.unallocated_amount, 1700)
		self.assertEqual(bank_transaction.payment_entries, [])

	# Check if ERPNext can correctly filter a linked payments based on the debit/credit amount
	def test_debit_credit_output(self):
		bank_transaction = frappe.get_doc(
			"Bank Transaction",
			dict(description="Auszahlung Karte MC/000002916 AUTOMAT 698769 K002 27.10. 14:07"),
		)
		linked_payments = get_linked_payments(
			bank_transaction.name,
			["payment_entry", "exact_match"],
			from_date=bank_transaction.date,
			to_date=utils.today(),
		)
		self.assertTrue(linked_payments[0]["paid_amount"])

	# Check error if already reconciled
	def test_already_reconciled(self):
		bank_transaction = frappe.get_doc(
			"Bank Transaction",
			dict(description="1512567 BG/000002918 OPSKATTUZWXXX AT776000000098709837 Herr G"),
		)
		payment = frappe.get_doc("Payment Entry", dict(party="Mr G", paid_amount=1200))
		vouchers = json.dumps(
			[
				{
					"payment_doctype": "Payment Entry",
					"payment_name": payment.name,
					"amount": bank_transaction.unallocated_amount,
				}
			]
		)
		reconcile_vouchers(bank_transaction.name, vouchers)

		bank_transaction = frappe.get_doc(
			"Bank Transaction",
			dict(description="1512567 BG/000002918 OPSKATTUZWXXX AT776000000098709837 Herr G"),
		)
		payment = frappe.get_doc("Payment Entry", dict(party="Mr G", paid_amount=1200))
		vouchers = json.dumps(
			[
				{
					"payment_doctype": "Payment Entry",
					"payment_name": payment.name,
					"amount": bank_transaction.unallocated_amount,
				}
			]
		)
		self.assertRaises(
			frappe.ValidationError,
			reconcile_vouchers,
			bank_transaction_name=bank_transaction.name,
			vouchers=vouchers,
		)

	# Raise an error if debitor transaction vs debitor payment
	def test_clear_sales_invoice(self):
		bank_transaction = frappe.get_doc(
			"Bank Transaction",
			dict(description="I2015000011 VD/000002514 ATWWXXX AT4701345000003510057 Bio"),
		)
		payment = frappe.get_doc("Sales Invoice", dict(customer="Fayva", status=["=", "Paid"]))
		vouchers = json.dumps(
			[
				{
					"payment_doctype": "Sales Invoice",
					"payment_name": payment.name,
					"amount": bank_transaction.unallocated_amount,
				}
			]
		)
		reconcile_vouchers(bank_transaction.name, vouchers=vouchers)

		self.assertEqual(
			frappe.db.get_value("Bank Transaction", bank_transaction.name, "unallocated_amount"), 0
		)
		self.assertTrue(
			frappe.db.get_value("Sales Invoice Payment", dict(parent=payment.name), "clearance_date")
			is not None
		)

	@if_lending_app_installed
	def test_matching_loan_repayment(self):
		from lending.loan_management.doctype.loan.test_loan import create_loan_accounts

		create_loan_accounts()
		bank_account = frappe.get_doc(
			{
				"doctype": "Bank Account",
				"account_name": "Payment Account",
				"bank": "Citi Bank",
				"account": "Payment Account - _TC",
			}
		).insert(ignore_if_duplicate=True)

		bank_transaction = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"description": "Loan Repayment - OPSKATTUZWXXX AT776000000098709837 Herr G",
				"date": "2018-10-27",
				"deposit": 500,
				"currency": "INR",
				"bank_account": bank_account.name,
			}
		).submit()

		repayment_entry = create_loan_and_repayment()

		linked_payments = get_linked_payments(bank_transaction.name, ["loan_repayment", "exact_match"])
		self.assertEqual(linked_payments[0]["name"], repayment_entry.name)

	def test_validate_currency_TC_ACC_270(self):
		bank_account = create_bank_account()
		account = frappe.get_doc("Account", frappe.get_value("Bank Account", bank_account, "account"))
		account.account_currency = "USD"
		account.save()

		bank_transaction = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"description": "Currency Mismatch Test",
				"date": "2025-01-01",
				"deposit": 1000,
				"currency": "INR",
				"bank_account": bank_account,
			}
		)

		self.assertRaises(frappe.ValidationError, bank_transaction.validate_currency)

	def test_validate_duplicate_references_TC_ACC_271(self):
		bt = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"description": "Duplicate Payment Entry",
				"date": "2025-01-01",
				"deposit": 1000,
				"currency": "INR",
				"bank_account": create_bank_account(),
			}
		)

		bt.append(
			"payment_entries",
			{
				"payment_document": "Payment Entry",
				"payment_entry": "PE-00001",
				"allocated_amount": 1000,
			},
		)
		bt.append(
			"payment_entries",
			{
				"payment_document": "Payment Entry",
				"payment_entry": "PE-00001",
				"allocated_amount": 1000,
			},
		)

		self.assertRaises(frappe.ValidationError, bt.validate_duplicate_references)

	def test_before_save_TC_ACC_272(self):
		bank_account = create_bank_account()
		doc1 = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"description": "Duplicate Check",
				"date": "2025-01-01",
				"deposit": 1000,
				"currency": "INR",
				"bank_account": bank_account,
				"reference_number": "DUP-001",
			}
		).insert()
		doc1.submit()

		doc2 = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"description": "Duplicate Check",
				"date": "2025-01-01",
				"deposit": 1000,
				"currency": "INR",
				"bank_account": bank_account,
				"reference_number": "DUP-001",
			}
		)

		self.assertRaises(frappe.ValidationError, doc2.before_save)

	def test_remove_payment_entries_TC_ACC_273(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		gl_account = create_gl_account("Remove PE Bank")
		bank_account = create_bank_account(gl_account=gl_account, bank_account_name="Remove PE Account")

		# Create a Purchase Invoice and Payment Entry
		pi = make_purchase_invoice(supplier="Conrad Electronic", qty=1, rate=1000)
		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account=gl_account)
		pe.reference_no = "Test-REF-001"
		pe.reference_date = "2025-01-01"
		pe.insert()
		pe.submit()

		# Create a Bank Transaction and link the Payment Entry
		bt = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"description": "Remove PE Test",
				"date": "2025-01-01",
				"deposit": 1000,
				"currency": "INR",
				"bank_account": bank_account,
			}
		)
		bt.append(
			"payment_entries",
			{
				"payment_document": "Payment Entry",
				"payment_entry": pe.name,
				"allocated_amount": 500,
			},
		)
		bt.insert()
		bt.submit()

		# Now call the method under test
		bt.remove_payment_entries()

		bt.reload()
		self.assertEqual(len(bt.payment_entries), 0)

	def test_remove_payment_entries_TC_ACC_274(self):
		gl_account = create_gl_account("Linked BT Bank")
		bank_account = create_bank_account(gl_account=gl_account, bank_account_name="Linked BT Account")

		# Create Main Bank Transaction
		bt_main = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"description": "Main BT",
				"date": "2025-01-01",
				"deposit": 1000,
				"currency": "INR",
				"bank_account": bank_account,
			}
		)
		bt_main.insert()
		bt_main.submit()

		bt_child = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"description": "Child BT",
				"date": "2025-01-02",
				"deposit": 500,
				"currency": "INR",
				"bank_account": bank_account,
			}
		)
		bt_child.append(
			"payment_entries",
			{
				"payment_document": "Bank Transaction",
				"payment_entry": bt_main.name,
				"allocated_amount": 500,
			},
		)
		bt_child.insert()
		bt_child.submit()

		bt_main.append(
			"payment_entries",
			{
				"payment_document": "Bank Transaction",
				"payment_entry": bt_child.name,
				"allocated_amount": 500,
			},
		)
		bt_main.save()
		bt_main.submit()

		# Test: remove entries in main BT (should call update_linked_bank_transaction)
		bt_main.remove_payment_entries()
		bt_main.reload()
		self.assertEqual(len(bt_main.payment_entries), 0)

	def test_allocate_payment_entries_all_paths_TC_ACC_275(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		gl_account = create_gl_account("Alloc Paths")
		bank_account = create_bank_account(gl_account=gl_account, bank_account_name="Alloc Paths")

		# Fully allocated (allocable_amount = 0 and should_clear)
		si_full = create_sales_invoice(customer="Fayva", qty=1, rate=100)
		pe_full = get_payment_entry("Sales Invoice", si_full.name, bank_account=gl_account)
		pe_full.reference_no = "REF-A"
		pe_full.reference_date = "2025-01-01"
		pe_full.insert()
		pe_full.submit()

		# Full allocation through dummy bank transaction
		bt_full = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"description": "Dummy full",
				"date": "2025-01-02",
				"deposit": 100,
				"currency": "INR",
				"bank_account": bank_account,
			}
		)
		bt_full.append(
			"payment_entries",
			{"payment_document": "Payment Entry", "payment_entry": pe_full.name, "allocated_amount": 100},
		)
		bt_full.insert()
		bt_full.submit()

		# Over-allocated (allocable_amount < 0)
		si_over = create_sales_invoice(customer="Fayva", qty=1, rate=100)
		pe_over = get_payment_entry("Sales Invoice", si_over.name, bank_account=gl_account)
		pe_over.reference_no = "REF-B"
		pe_over.reference_date = "2025-01-01"
		pe_over.insert()
		pe_over.submit()

		# Allocate more than voucher amount manually
		bt_over = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"description": "Over allocate",
				"date": "2025-01-02",
				"deposit": 200,
				"currency": "INR",
				"bank_account": bank_account,
			}
		)
		bt_over.append(
			"payment_entries",
			{"payment_document": "Payment Entry", "payment_entry": pe_over.name, "allocated_amount": 150},
		)
		bt_over.insert()
		bt_over.submit()

		# Will be skipped due to remaining_amount = 0
		si_skip = create_sales_invoice(customer="Fayva", qty=1, rate=100)
		pe_skip = get_payment_entry("Sales Invoice", si_skip.name, bank_account=gl_account)
		pe_skip.reference_no = "REF-C"
		pe_skip.reference_date = "2025-01-01"
		pe_skip.insert()
		pe_skip.submit()

		# Linked Bank Transaction to test .update_linked_bank_transaction()
		bt_linked = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"description": "Linked child",
				"date": "2025-01-03",
				"deposit": 50,
				"currency": "INR",
				"bank_account": bank_account,
			}
		)
		bt_linked.insert()
		bt_linked.submit()

		# BT to allocate all above
		bt = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"description": "Master allocate test",
				"date": "2025-01-05",
				"deposit": 150,
				"currency": "INR",
				"bank_account": bank_account,
			}
		)

		# Append all entries
		bt.append(
			"payment_entries",
			{"payment_document": "Payment Entry", "payment_entry": pe_full.name, "allocated_amount": 0},
		)  # allocable=0
		bt.append(
			"payment_entries",
			{"payment_document": "Payment Entry", "payment_entry": pe_over.name, "allocated_amount": 0},
		)  # over-alloc
		bt.append(
			"payment_entries",
			{"payment_document": "Payment Entry", "payment_entry": pe_skip.name, "allocated_amount": 0},
		)  # will be skipped
		bt.append(
			"payment_entries",
			{"payment_document": "Bank Transaction", "payment_entry": bt_linked.name, "allocated_amount": 0},
		)  # triggers update_linked_bank_transaction

		bt.insert()
		with self.assertRaises(frappe.ValidationError) as context:
			bt.submit()

		self.assertIn("is over-allocated by", str(context.exception))

		# Run and expect one error during over-allocation
		with self.assertRaises(frappe.ValidationError) as context:
			bt.allocate_payment_entries()

		self.assertIn("over-allocated", str(context.exception))


@if_lending_app_installed
def clear_loan_transactions():
	frappe.db.delete("Loan Repayment")


def create_bank_account(
	bank_name="Citi Bank", gl_account="_Test Bank - _TC", bank_account_name="Checking Account"
):
	try:
		frappe.get_doc(
			{
				"doctype": "Bank",
				"bank_name": bank_name,
			}
		).insert(ignore_if_duplicate=True)
	except frappe.DuplicateEntryError:
		pass

	try:
		bank_account = frappe.get_doc(
			{
				"doctype": "Bank Account",
				"account_name": bank_account_name,
				"bank": bank_name,
				"account": gl_account,
			}
		).insert(ignore_if_duplicate=True)
	except frappe.DuplicateEntryError:
		pass

	return bank_account.name


def create_gl_account(gl_account_name="_Test Bank - _TC"):
	gl_account = frappe.get_doc(
		{
			"doctype": "Account",
			"company": "_Test Company",
			"parent_account": "Current Assets - _TC",
			"account_type": "Bank",
			"is_group": 0,
			"account_name": gl_account_name,
		}
	).insert()
	return gl_account.name


def add_transactions(bank_account="_Test Bank - _TC"):
	doc = frappe.get_doc(
		{
			"doctype": "Bank Transaction",
			"description": "1512567 BG/000002918 OPSKATTUZWXXX AT776000000098709837 Herr G",
			"date": "2018-10-23",
			"deposit": 1200,
			"currency": "INR",
			"bank_account": bank_account,
		}
	).insert()
	doc.submit()

	doc = frappe.get_doc(
		{
			"doctype": "Bank Transaction",
			"description": "1512567 BG/000003025 OPSKATTUZWXXX AT776000000098709849 Herr G",
			"date": "2018-10-23",
			"deposit": 1700,
			"currency": "INR",
			"bank_account": bank_account,
		}
	).insert()
	doc.submit()

	doc = frappe.get_doc(
		{
			"doctype": "Bank Transaction",
			"description": "Re 95282925234 FE/000002917 AT171513000281183046 Conrad Electronic",
			"date": "2018-10-26",
			"withdrawal": 690,
			"currency": "INR",
			"bank_account": bank_account,
		}
	).insert()
	doc.submit()

	doc = frappe.get_doc(
		{
			"doctype": "Bank Transaction",
			"description": "Auszahlung Karte MC/000002916 AUTOMAT 698769 K002 27.10. 14:07",
			"date": "2018-10-27",
			"deposit": 3900,
			"currency": "INR",
			"bank_account": bank_account,
		}
	).insert()
	doc.submit()

	doc = frappe.get_doc(
		{
			"doctype": "Bank Transaction",
			"description": "I2015000011 VD/000002514 ATWWXXX AT4701345000003510057 Bio",
			"date": "2018-10-27",
			"withdrawal": 109080,
			"currency": "INR",
			"bank_account": bank_account,
		}
	).insert()
	doc.submit()


def add_vouchers(gl_account="_Test Bank - _TC"):
	from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

	try:
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_group": "All Supplier Groups",
				"supplier_type": "Company",
				"supplier_name": "Conrad Electronic",
			}
		).insert(ignore_if_duplicate=True)

	except frappe.DuplicateEntryError:
		pass

	pi = make_purchase_invoice(supplier="Conrad Electronic", qty=1, rate=690)

	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account=gl_account)
	pe.reference_no = "Conrad Oct 18"
	pe.reference_date = "2018-10-24"
	pe.insert(ignore_permissions=True)
	pe.submit()

	try:
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_group": "All Supplier Groups",
				"supplier_type": "Company",
				"supplier_name": "Mr G",
			}
		).insert(ignore_if_duplicate=True)
	except frappe.DuplicateEntryError:
		pass

	pi = make_purchase_invoice(supplier="Mr G", qty=1, rate=1200)
	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account=gl_account)
	pe.reference_no = "Herr G Oct 18"
	pe.reference_date = "2018-10-24"
	pe.insert(ignore_permissions=True)
	pe.submit()

	pi = make_purchase_invoice(supplier="Mr G", qty=1, rate=1700)
	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account=gl_account)
	pe.reference_no = "Herr G Nov 18"
	pe.reference_date = "2018-11-01"
	pe.insert(ignore_permissions=True)
	pe.submit()

	try:
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_group": "All Supplier Groups",
				"supplier_type": "Company",
				"supplier_name": "Poore Simon's",
			}
		).insert(ignore_if_duplicate=True)
	except frappe.DuplicateEntryError:
		pass

	try:
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_group": "All Customer Groups",
				"customer_type": "Company",
				"customer_name": "Poore Simon's",
			}
		).insert(ignore_if_duplicate=True)
	except frappe.DuplicateEntryError:
		pass

	pi = make_purchase_invoice(supplier="Poore Simon's", qty=1, rate=3900, is_paid=1, do_not_save=1)
	pi.cash_bank_account = gl_account
	pi.insert(ignore_permissions=True)
	pi.submit()
	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account=gl_account)
	pe.reference_no = "Poore Simon's Oct 18"
	pe.reference_date = "2018-10-28"
	pe.paid_amount = 690
	pe.received_amount = 690
	pe.insert(ignore_permissions=True)
	pe.submit()

	si = create_sales_invoice(customer="Poore Simon's", qty=1, rate=3900)
	pe = get_payment_entry("Sales Invoice", si.name, bank_account=gl_account)
	pe.reference_no = "Poore Simon's Oct 18"
	pe.reference_date = "2018-10-28"
	pe.insert(ignore_permissions=True)
	pe.submit()

	try:
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_group": "All Customer Groups",
				"customer_type": "Company",
				"customer_name": "Fayva",
			}
		).insert(ignore_if_duplicate=True)
	except frappe.DuplicateEntryError:
		pass

	mode_of_payment = frappe.get_doc({"doctype": "Mode of Payment", "name": "Wire Transfer"})

	set_default_account_for_mode_of_payment(mode_of_payment, "_Test Company", gl_account)

	si = create_sales_invoice(customer="Fayva", qty=1, rate=109080, do_not_save=1)
	si.is_pos = 1
	si.append("payments", {"mode_of_payment": "Wire Transfer", "amount": 109080})
	si.insert()
	si.submit()


@if_lending_app_installed
def create_loan_and_repayment():
	from lending.loan_management.doctype.loan.test_loan import (
		create_loan,
		create_loan_product,
		create_repayment_entry,
		make_loan_disbursement_entry,
	)
	from lending.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import (
		process_loan_interest_accrual_for_term_loans,
	)

	from erpnext.setup.doctype.employee.test_employee import make_employee

	create_loan_product(
		"Personal Loan",
		"Personal Loan",
		500000,
		8.4,
		is_term_loan=1,
		mode_of_payment="Cash",
		disbursement_account="Disbursement Account - _TC",
		payment_account="Payment Account - _TC",
		loan_account="Loan Account - _TC",
		interest_income_account="Interest Income Account - _TC",
		penalty_income_account="Penalty Income Account - _TC",
	)

	applicant = make_employee("test_bank_reco@loan.com", company="_Test Company")
	loan = create_loan(applicant, "Personal Loan", 5000, "Repay Over Number of Periods", 20)
	loan = frappe.get_doc(
		{
			"doctype": "Loan",
			"applicant_type": "Employee",
			"company": "_Test Company",
			"applicant": applicant,
			"loan_product": "Personal Loan",
			"loan_amount": 5000,
			"repayment_method": "Repay Fixed Amount per Period",
			"monthly_repayment_amount": 500,
			"repayment_start_date": "2018-09-27",
			"is_term_loan": 1,
			"posting_date": "2018-09-27",
		}
	).insert()

	make_loan_disbursement_entry(loan.name, loan.loan_amount, disbursement_date="2018-09-27")
	process_loan_interest_accrual_for_term_loans(posting_date="2018-10-27")

	repayment_entry = create_repayment_entry(
		loan.name,
		applicant,
		"2018-10-27",
		500,
	)
	repayment_entry.submit()
	return repayment_entry
