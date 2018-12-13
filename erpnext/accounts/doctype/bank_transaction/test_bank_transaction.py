# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
from erpnext.accounts.page.bank_reconciliation.bank_reconciliation import reconcile, get_linked_payments

test_dependencies = ["Item", "Cost Center"]

class TestBankTransaction(unittest.TestCase):
	def setUp(self):
		add_transactions()
		add_payments()

	def tearDown(self):
		for bt in frappe.get_all("Bank Transaction"):
			doc = frappe.get_doc("Bank Transaction", bt.name)
			doc.cancel()
			doc.delete()

		for pe in frappe.get_all("Payment Entry"):
			doc = frappe.get_doc("Payment Entry", pe.name)
			doc.cancel()
			doc.delete()

		frappe.flags.test_bank_transactions_created = False
		frappe.flags.test_payments_created = False

	# This test checks if ERPNext is able to provide a linked payment for a bank transaction based on the amount of the bank transaction.
	def test_linked_payments(self):
		bank_transaction = frappe.get_doc("Bank Transaction", dict(description="Re 95282925234 FE/000002917 AT171513000281183046 Conrad Electronic"))
		linked_payments = get_linked_payments(bank_transaction.name)
		self.assertTrue(linked_payments[0].party == "Conrad Electronic")

	# This test validates a simple reconciliation leading to the clearance of the bank transaction and the payment
	def test_reconcile(self):
		bank_transaction = frappe.get_doc("Bank Transaction", dict(description="1512567 BG/000002918 OPSKATTUZWXXX AT776000000098709837 Herr G"))
		payment = frappe.get_doc("Payment Entry", dict(party="Mr G", paid_amount=1200))
		reconcile(bank_transaction.name, "Payment Entry", payment.name)

		unallocated_amount = frappe.db.get_value("Bank Transaction", bank_transaction.name, "unallocated_amount")
		self.assertTrue(unallocated_amount == 0)

		clearance_date = frappe.db.get_value("Payment Entry", payment.name, "clearance_date")
		self.assertTrue(clearance_date is not None)

	# Check if ERPNext can correctly fetch a linked payment based on the party
	def test_linked_payments_based_on_party(self):
		bank_transaction = frappe.get_doc("Bank Transaction", dict(description="1512567 BG/000003025 OPSKATTUZWXXX AT776000000098709849 Herr G"))
		linked_payments = get_linked_payments(bank_transaction.name)
		self.assertTrue(len(linked_payments)==1)

	# Check if ERPNext can correctly filter a linked payments based on the debit/credit amount
	def test_debit_credit_output(self):
		bank_transaction = frappe.get_doc("Bank Transaction", dict(description="Auszahlung Karte MC/000002916 AUTOMAT 698769 K002 27.10. 14:07"))
		linked_payments = get_linked_payments(bank_transaction.name)
		self.assertTrue(linked_payments[0].payment_type == "Pay")

	# Check error if already reconciled
	def test_already_reconciled(self):
		bank_transaction = frappe.get_doc("Bank Transaction", dict(description="1512567 BG/000002918 OPSKATTUZWXXX AT776000000098709837 Herr G"))
		payment = frappe.get_doc("Payment Entry", dict(party="Mr G", paid_amount=1200))
		reconcile(bank_transaction.name, "Payment Entry", payment.name)

		bank_transaction = frappe.get_doc("Bank Transaction", dict(description="1512567 BG/000002918 OPSKATTUZWXXX AT776000000098709837 Herr G"))
		payment = frappe.get_doc("Payment Entry", dict(party="Mr G", paid_amount=1200))
		self.assertRaises(frappe.ValidationError, reconcile, bank_transaction=bank_transaction.name, payment_doctype="Payment Entry", payment_name=payment.name)

	# Raise an error if creditor transaction vs creditor payment
	def test_invalid_creditor_reconcilation(self):
		bank_transaction = frappe.get_doc("Bank Transaction", dict(description="I2015000011 VD/000002514 ATWWXXX AT4701345000003510057 Bio"))
		payment = frappe.get_doc("Payment Entry", dict(party="Conrad Electronic", paid_amount=690))
		self.assertRaises(frappe.ValidationError, reconcile, bank_transaction=bank_transaction.name, payment_doctype="Payment Entry", payment_name=payment.name)

	# Raise an error if debitor transaction vs debitor payment
	def test_invalid_debitor_reconcilation(self):
		bank_transaction = frappe.get_doc("Bank Transaction", dict(description="Auszahlung Karte MC/000002916 AUTOMAT 698769 K002 27.10. 14:07"))
		payment = frappe.get_doc("Payment Entry", dict(party="Fayva", paid_amount=109080))
		self.assertRaises(frappe.ValidationError, reconcile, bank_transaction=bank_transaction.name, payment_doctype="Payment Entry", payment_name=payment.name)

def add_transactions():
	if frappe.flags.test_bank_transactions_created:
		return

	frappe.set_user("Administrator")
	try:
		frappe.get_doc({
			"doctype": "Bank",
			"bank_name":"Citi Bank",
		}).insert()

		frappe.get_doc({
			"doctype": "Bank Account",
			"account_name":"Checking Account",
			"bank": "Citi Bank",
			"account": "_Test Bank - _TC"
		}).insert()
	except frappe.DuplicateEntryError:
		pass

	doc = frappe.get_doc({
		"doctype": "Bank Transaction",
		"description":"1512567 BG/000002918 OPSKATTUZWXXX AT776000000098709837 Herr G",
		"date": "2018-10-23",
		"debit": 1200,
		"currency": "INR",
		"bank_account": "Checking Account - Citi Bank"
	}).insert()
	doc.submit()

	doc = frappe.get_doc({
		"doctype": "Bank Transaction",
		"description":"1512567 BG/000003025 OPSKATTUZWXXX AT776000000098709849 Herr G",
		"date": "2018-10-23",
		"debit": 1700,
		"currency": "INR",
		"bank_account": "Checking Account - Citi Bank"
	}).insert()
	doc.submit()

	doc = frappe.get_doc({
		"doctype": "Bank Transaction",
		"description":"Re 95282925234 FE/000002917 AT171513000281183046 Conrad Electronic",
		"date": "2018-10-26",
		"debit": 690,
		"currency": "INR",
		"bank_account": "Checking Account - Citi Bank"
	}).insert()
	doc.submit()

	doc = frappe.get_doc({
		"doctype": "Bank Transaction",
		"description":"Auszahlung Karte MC/000002916 AUTOMAT 698769 K002 27.10. 14:07",
		"date": "2018-10-27",
		"debit": 3900,
		"currency": "INR",
		"bank_account": "Checking Account - Citi Bank"
	}).insert()
	doc.submit()

	doc = frappe.get_doc({
		"doctype": "Bank Transaction",
		"description":"I2015000011 VD/000002514 ATWWXXX AT4701345000003510057 Bio",
		"date": "2018-10-27",
		"credit": 109080,
		"currency": "INR",
		"bank_account": "Checking Account - Citi Bank"
	}).insert()
	doc.submit()

	frappe.flags.test_bank_transactions_created = True

def add_payments():
	if frappe.flags.test_payments_created:
		return

	frappe.set_user("Administrator")

	try:
		frappe.get_doc({
			"doctype": "Supplier",
			"supplier_group":"All Supplier Groups",
			"supplier_type": "Company",
			"supplier_name": "Conrad Electronic"
		}).insert()

	except frappe.DuplicateEntryError:
		pass

	pi = make_purchase_invoice(supplier="Conrad Electronic", qty=1, rate=690)
	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")
	pe.reference_no = "Conrad Oct 18"
	pe.reference_date = "2018-10-24"
	pe.insert()
	pe.submit()

	try:
		frappe.get_doc({
			"doctype": "Supplier",
			"supplier_group":"All Supplier Groups",
			"supplier_type": "Company",
			"supplier_name": "Mr G"
		}).insert()
	except frappe.DuplicateEntryError:
		pass

	pi = make_purchase_invoice(supplier="Mr G", qty=1, rate=1200)
	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")
	pe.reference_no = "Herr G Oct 18"
	pe.reference_date = "2018-10-24"
	pe.insert()
	pe.submit()

	pi = make_purchase_invoice(supplier="Mr G", qty=1, rate=1700)
	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")
	pe.reference_no = "Herr G Nov 18"
	pe.reference_date = "2018-11-01"
	pe.insert()
	pe.submit()

	try:
		frappe.get_doc({
			"doctype": "Supplier",
			"supplier_group":"All Supplier Groups",
			"supplier_type": "Company",
			"supplier_name": "Poore Simon's"
		}).insert()
	except frappe.DuplicateEntryError:
		pass

	try:
		frappe.get_doc({
			"doctype": "Customer",
			"customer_group":"All Customer Groups",
			"customer_type": "Company",
			"customer_name": "Poore Simon's"
		}).insert()
	except frappe.DuplicateEntryError:
		pass

	pi = make_purchase_invoice(supplier="Poore Simon's", qty=1, rate=3900)
	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")
	pe.reference_no = "Poore Simon's Oct 18"
	pe.reference_date = "2018-10-28"
	pe.insert()
	pe.submit()

	si = create_sales_invoice(customer="Poore Simon's", qty=1, rate=3900)
	pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
	pe.reference_no = "Poore Simon's Oct 18"
	pe.reference_date = "2018-10-28"
	pe.insert()
	pe.submit()

	try:
		frappe.get_doc({
			"doctype": "Customer",
			"customer_group":"All Customer Groups",
			"customer_type": "Company",
			"customer_name": "Fayva"
		}).insert()
	except frappe.DuplicateEntryError:
		pass

	si = create_sales_invoice(customer="Fayva", qty=1, rate=109080)
	pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
	pe.reference_no = "Fayva Oct 18"
	pe.reference_date = "2018-10-29"
	pe.insert()
	pe.submit()

	frappe.flags.test_payments_created = True