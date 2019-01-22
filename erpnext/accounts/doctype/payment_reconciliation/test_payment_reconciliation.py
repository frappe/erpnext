# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import unittest
from frappe.utils import nowdate
from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import get_advance_journal_entries,\
	get_advance_payment_entries
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.utils import get_balance_on_voucher, reconcile_against_document


class TestPaymentReconciliation(unittest.TestCase):
	def setUp(self):
		self.customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": frappe.generate_hash(length=10),
			"customer_group": "_Test Customer Group",
			"customer_type": "Individual",
			"territory": "_Test Territory"
		}).insert()
		# self.supplier = frappe.get_doc({
		# 	"doctype": "Supplier",
		# 	"supplier_name": frappe.generate_hash(length=10),
		# 	"supplier_group": "_Test Supplier Group"
		# }).insert()

	def test_reconcile_advance_journal_entries(self):
		self.assertFalse(get_advance_journal_entries(self.customer.doctype, self.customer.name, "_Test Receivable - _TC",
			"Sales Order", against_all_orders=True))

		# Test records
		jv_simple = make_payment_jv(self.customer, 100)
		jv_multiple_rows = make_payment_jv(self.customer, 300, unallocated_rows=3)

		jv_half_returned = make_payment_jv(self.customer, 200)
		_jv_return = make_payment_jv(self.customer, 0, jv_half_returned.doctype, jv_half_returned.name, -100)

		_jv_receivable = make_payment_jv(self.customer, -100)
		jv_half_allocated = make_payment_jv(self.customer, 100, _jv_receivable.doctype, _jv_receivable.name, 100)

		so = make_sales_order(self.customer)
		jv_against_so = make_payment_jv(self.customer, 100, so.doctype, so.name, 100)

		# Test get_advance_journal_entries
		advances = get_advance_journal_entries(self.customer.doctype, self.customer.name, "_Test Receivable - _TC",
			"Sales Order", against_all_orders=True)
		advance_vouchers = {}
		for d in advances:
			advance_vouchers.setdefault(d.reference_name, [])
			advance_vouchers[d.reference_name].append(d)

		self.assertEqual(len(advance_vouchers[jv_simple.name]), 1)
		self.assertEqual(advance_vouchers[jv_simple.name][0].amount, 100)

		self.assertEqual(len(advance_vouchers[jv_multiple_rows.name]), 1)
		self.assertEqual(advance_vouchers[jv_multiple_rows.name][0].amount, 300)

		self.assertEqual(len(advance_vouchers[jv_half_returned.name]), 1)
		self.assertEqual(advance_vouchers[jv_half_returned.name][0].amount, 100)

		self.assertEqual(len(advance_vouchers[jv_half_allocated.name]), 1)
		self.assertEqual(advance_vouchers[jv_half_allocated.name][0].amount, 100)

		self.assertEqual(len(advance_vouchers[jv_against_so.name]), 2)
		self.assertEqual(advance_vouchers[jv_against_so.name][0].amount, 100)
		self.assertEqual(advance_vouchers[jv_against_so.name][0].reference_row, jv_against_so.accounts[2].name)
		self.assertEqual(advance_vouchers[jv_against_so.name][1].amount, 100)

		# Test reconcile_against_document
		jv_receivable = make_payment_jv(self.customer, -5000)

		# Full allocation
		lst = [frappe._dict({
			'voucher_type': jv_simple.doctype,
			'voucher_no': jv_simple.name,
			'voucher_detail_no': None,
			'against_voucher_type': jv_receivable.doctype,
			'against_voucher': jv_receivable.name,
			'account': "_Test Receivable - _TC",
			'party_type': "Customer",
			'party': self.customer.name,
			'dr_or_cr': "credit_in_account_currency",
			'unadjusted_amount': 100,
			'allocated_amount': 100
		})]
		reconcile_against_document(lst)
		self.assertEqual(get_balance_on_voucher(jv_receivable.doctype, jv_receivable.name, "Customer", self.customer.name, "_Test Receivable - _TC"),
			4900)
		self.assertTrue(frappe.db.sql("""select name from `tabJournal Entry Account`
			where name=%s and reference_name=%s and credit_in_account_currency=%s and docstatus=1
		""", [jv_simple.accounts[1].name, jv_receivable.name, 100]))

		# Multiple row partial allocation
		lst = [frappe._dict({
			'voucher_type': jv_multiple_rows.doctype,
			'voucher_no': jv_multiple_rows.name,
			'voucher_detail_no': None,
			'against_voucher_type': jv_receivable.doctype,
			'against_voucher': jv_receivable.name,
			'account': "_Test Receivable - _TC",
			'party_type': "Customer",
			'party': self.customer.name,
			'dr_or_cr': "credit_in_account_currency",
			'unadjusted_amount': 300,
			'allocated_amount': 230
		})]
		reconcile_against_document(lst)
		self.assertEqual(get_balance_on_voucher(jv_receivable.doctype, jv_receivable.name, "Customer", self.customer.name, "_Test Receivable - _TC"),
			4670)
		self.assertTrue(frappe.db.sql("""select count(*) from `tabJournal Entry Account`
			where parent=%s and reference_name=%s and party_type='Customer' and party=%s and account='_Test Receivable - _TC'
			and credit_in_account_currency=%s and docstatus=1
			having count(*) = 2
		""", [jv_multiple_rows.name, jv_receivable.name, self.customer.name, 100]))
		self.assertTrue(frappe.db.sql("""select name from `tabJournal Entry Account`
			where parent=%s and reference_name=%s and party_type='Customer' and party=%s and account='_Test Receivable - _TC'
			and credit_in_account_currency=%s and docstatus=1
		""", [jv_multiple_rows.name, jv_receivable.name, self.customer.name, 30]))
		self.assertTrue(frappe.db.sql("""select name from `tabJournal Entry Account`
			where parent=%s and party_type='Customer' and party=%s and ifnull(reference_name, '') = ''
			and account='_Test Receivable - _TC' and credit_in_account_currency=%s and docstatus=1
		""", [jv_multiple_rows.name, self.customer.name, 70]))

		# Attempt to over allocate a partially returned/knocked-off jv
		lst = [frappe._dict({
			'voucher_type': jv_half_returned.doctype,
			'voucher_no': jv_half_returned.name,
			'voucher_detail_no': None,
			'against_voucher_type': jv_receivable.doctype,
			'against_voucher': jv_receivable.name,
			'account': "_Test Receivable - _TC",
			'party_type': "Customer",
			'party': self.customer.name,
			'dr_or_cr': "credit_in_account_currency",
			'unadjusted_amount': 200,
			'allocated_amount': 200
		})]
		self.assertRaises(frappe.ValidationError, reconcile_against_document, lst)

		# Attempt to over allocate a partially allocated jv
		lst = [frappe._dict({
			'voucher_type': jv_half_allocated.doctype,
			'voucher_no': jv_half_allocated.name,
			'voucher_detail_no': None,
			'against_voucher_type': jv_receivable.doctype,
			'against_voucher': jv_receivable.name,
			'account': "_Test Receivable - _TC",
			'party_type': "Customer",
			'party': self.customer.name,
			'dr_or_cr': "credit_in_account_currency",
			'unadjusted_amount': 200,
			'allocated_amount': 200
		})]
		self.assertRaises(frappe.ValidationError, reconcile_against_document, lst)

		# Sales Order advance reallocation
		lst = [frappe._dict({
			'voucher_type': jv_against_so.doctype,
			'voucher_no': jv_against_so.name,
			'voucher_detail_no': jv_against_so.accounts[2].name,
			'against_voucher_type': jv_receivable.doctype,
			'against_voucher': jv_receivable.name,
			'account': "_Test Receivable - _TC",
			'party_type': "Customer",
			'party': self.customer.name,
			'dr_or_cr': "credit_in_account_currency",
			'unadjusted_amount': 100,
			'allocated_amount': 100
		})]
		reconcile_against_document(lst)
		self.assertEqual(get_balance_on_voucher(jv_receivable.doctype, jv_receivable.name, "Customer", self.customer.name, "_Test Receivable - _TC"),
			4570)
		self.assertEqual(get_balance_on_voucher(so.doctype, so.name, "Customer", self.customer.name, "_Test Receivable - _TC"),
			0)
		self.assertEqual(frappe.db.get_value("Sales Order", so.name, "advance_paid"),
			0)
		self.assertTrue(frappe.db.sql("""select name from `tabJournal Entry Account`
			where name=%s and reference_name=%s and credit_in_account_currency=%s and docstatus=1
		""", [jv_against_so.accounts[2].name, jv_receivable.name, 100]))

		# Test get_advance_payment_entries after reconciliation
		advances = get_advance_journal_entries(self.customer.doctype, self.customer.name, "_Test Receivable - _TC",
			"Sales Order", against_all_orders=True)
		advance_vouchers = {}
		for d in advances:
			advance_vouchers.setdefault(d.reference_name, [])
			advance_vouchers[d.reference_name].append(d)

		self.assertFalse(advance_vouchers.get(jv_simple.name))

		self.assertEqual(len(advance_vouchers[jv_multiple_rows.name]), 1)
		self.assertEqual(advance_vouchers[jv_multiple_rows.name][0].amount, 70)

		self.assertEqual(len(advance_vouchers[jv_against_so.name]), 1)
		self.assertEqual(advance_vouchers[jv_against_so.name][0].amount, 100)

	def test_reconcile_advance_payment_entries(self):
		self.assertFalse(get_advance_payment_entries(self.customer.doctype, self.customer.name, "_Test Receivable - _TC",
			"Sales Order", against_all_orders=True))

		# Test records
		_jv_receivable = make_payment_jv(self.customer, -100)

		so = make_sales_order(self.customer)
		pe_against_so = make_payment_entry(self.customer, 100, so.doctype, so.name, 100)
		pe_unallocated = make_payment_entry(self.customer, 100)
		pe_half_allocated = make_payment_entry(self.customer, 100, _jv_receivable.doctype, _jv_receivable.name, 100)

		# Test get_advance_payment_entries
		advances = get_advance_payment_entries(self.customer.doctype, self.customer.name, "_Test Receivable - _TC",
			"Sales Order", against_all_orders=True)
		advance_vouchers = {}
		for d in advances:
			advance_vouchers.setdefault(d.reference_name, [])
			advance_vouchers[d.reference_name].append(d)

		import pprint
		print("-------------------------------")
		pprint.pprint(advance_vouchers)
		print("-------------------------------")

		self.assertEqual(len(advance_vouchers[pe_against_so.name]), 2)
		self.assertEqual(advance_vouchers[pe_against_so.name][0].reference_row, pe_against_so.references[0].name)
		self.assertEqual(advance_vouchers[pe_against_so.name][0].amount, 100)
		self.assertEqual(advance_vouchers[pe_against_so.name][1].amount, 100)

		self.assertEqual(len(advance_vouchers[pe_unallocated.name]), 1)
		self.assertEqual(advance_vouchers[pe_unallocated.name][0].amount, 100)

		self.assertEqual(len(advance_vouchers[pe_half_allocated.name]), 1)
		self.assertEqual(advance_vouchers[pe_half_allocated.name][0].amount, 100)

		# Test reconcile_against_document
		jv_receivable = make_payment_jv(self.customer, -5000)

		# Full allocation
		lst = [frappe._dict({
			'voucher_type': pe_unallocated.doctype,
			'voucher_no': pe_unallocated.name,
			'voucher_detail_no': None,
			'against_voucher_type': jv_receivable.doctype,
			'against_voucher': jv_receivable.name,
			'account': "_Test Receivable - _TC",
			'party_type': "Customer",
			'party': self.customer.name,
			'dr_or_cr': "credit_in_account_currency",
			'unadjusted_amount': 100,
			'allocated_amount': 100
		})]
		reconcile_against_document(lst)
		self.assertEqual(get_balance_on_voucher(jv_receivable.doctype, jv_receivable.name, "Customer", self.customer.name, "_Test Receivable - _TC"),
			4900)
		self.assertTrue(frappe.db.sql("""select name from `tabPayment Entry Reference`
			where parent=%s and reference_name=%s and allocated_amount=%s and docstatus=1
		""", [pe_unallocated.name, jv_receivable.name, 100]))
		self.assertEqual(frappe.get_value("Payment Entry", pe_unallocated.name, "unallocated_amount"), 0)

		# Attempt to over allocate a partially allocated pe
		lst = [frappe._dict({
			'voucher_type': pe_half_allocated.doctype,
			'voucher_no': pe_half_allocated.name,
			'voucher_detail_no': None,
			'against_voucher_type': jv_receivable.doctype,
			'against_voucher': jv_receivable.name,
			'account': "_Test Receivable - _TC",
			'party_type': "Customer",
			'party': self.customer.name,
			'dr_or_cr': "credit_in_account_currency",
			'unadjusted_amount': 200,
			'allocated_amount': 200
		})]
		self.assertRaises(frappe.ValidationError, reconcile_against_document, lst)

		# Sales Order advance reallocation
		lst = [frappe._dict({
			'voucher_type': pe_against_so.doctype,
			'voucher_no': pe_against_so.name,
			'voucher_detail_no': pe_against_so.references[0].name,
			'against_voucher_type': jv_receivable.doctype,
			'against_voucher': jv_receivable.name,
			'account': "_Test Receivable - _TC",
			'party_type': "Customer",
			'party': self.customer.name,
			'dr_or_cr': "credit_in_account_currency",
			'unadjusted_amount': 100,
			'allocated_amount': 100
		})]
		reconcile_against_document(lst)
		self.assertEqual(get_balance_on_voucher(jv_receivable.doctype, jv_receivable.name, "Customer", self.customer.name, "_Test Receivable - _TC"),
			4800)
		self.assertEqual(get_balance_on_voucher(so.doctype, so.name, "Customer", self.customer.name, "_Test Receivable - _TC"),
			0)
		self.assertEqual(frappe.db.get_value("Sales Order", so.name, "advance_paid"),
			0)
		self.assertTrue(frappe.db.sql("""select name from `tabPayment Entry Reference`
			where parent=%s and reference_name=%s and allocated_amount=%s and docstatus=1
		""", [pe_unallocated.name, jv_receivable.name, 100]))
		self.assertEqual(frappe.get_value("Payment Entry", pe_against_so.name, "unallocated_amount"), 100)

		# Test get_advance_payment_entries after reconciliation
		advances = get_advance_payment_entries(self.customer.doctype, self.customer.name, "_Test Receivable - _TC",
			"Sales Order", against_all_orders=True)
		advance_vouchers = {}
		for d in advances:
			advance_vouchers.setdefault(d.reference_name, [])
			advance_vouchers[d.reference_name].append(d)

		self.assertFalse(advance_vouchers.get(pe_unallocated.name))
		self.assertEqual(len(advance_vouchers[pe_against_so.name]), 1)
		self.assertEqual(advance_vouchers[pe_against_so.name][0].amount, 100)


def make_payment_entry(party, unallocated_amount, against_dt=None, against_dn=None, against_amount=None):
	doc = frappe.new_doc("Payment Entry")
	doc.company = "_Test Company"
	doc.party_type = party.doctype
	doc.party = party.name
	doc.party_account = "_Test Payable - _TC" if doc.party_type == "Supplier" else "_Test Receivable - _TC"
	doc.payment_type = "Pay" if doc.party_type == "Supplier" else "Receive"
	doc.paid_from = "_Test Bank - _TC" if doc.party_type == "Supplier" else doc.party_account
	doc.paid_to = doc.party_account if doc.party_type == "Supplier" else "_Test Bank - _TC"
	doc.exchange_rate = 1
	doc.allocate_payment_amount = 0
	doc.reference_no = "1"
	doc.reference_date = nowdate()

	if against_dt and against_dn and against_amount:
		doc.paid_amount = doc.received_amount = unallocated_amount + against_amount
		doc.unallocated_amount = unallocated_amount + against_amount
		doc.append("references", {
			'reference_doctype': against_dt,
			'reference_name': against_dn,
			'allocated_amount': against_amount
		})
	else:
		doc.paid_amount = doc.received_amount = unallocated_amount
		doc.unallocated_amount = unallocated_amount

	doc.set_missing_values()
	doc.insert()
	doc.submit()

	import pprint
	print("-------------------------------")
	pprint.pprint(doc.as_dict())
	print("-------------------------------")

	return doc


def make_payment_jv(party, unallocated_amount, against_dt=None, against_dn=None, against_amount=None,
		unallocated_rows=None):
	from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

	party_type = party.doctype
	party_account = "_Test Payable - _TC" if party_type == "Supplier" else "_Test Receivable - _TC"

	total_amount = unallocated_amount
	if against_dt and against_dn and against_amount:
		total_amount += against_amount
	if party_type == "Supplier":
		total_amount = -1 * total_amount

	jv = make_journal_entry("_Test Bank - _TC", party_account, total_amount, save=False)
	jv.accounts[1].update({"party_type": party_type, "party": party.name})
	if jv.accounts[1].debit_in_account_currency:
		jv.accounts[1].debit_in_account_currency = abs(unallocated_amount)
	else:
		jv.accounts[1].credit_in_account_currency = abs(unallocated_amount)

	if unallocated_rows:
		if jv.accounts[1].debit_in_account_currency:
			jv.accounts[1].debit_in_account_currency = unallocated_amount / unallocated_rows
		else:
			jv.accounts[1].credit_in_account_currency = unallocated_amount / unallocated_rows

		for i in range(unallocated_rows-1):
			jv.append("accounts", jv.accounts[1].as_dict())

	if against_dt and against_dn and against_amount:
		if unallocated_amount:
			allocated_row = jv.append("accounts", jv.accounts[1].as_dict())
		else:
			allocated_row = jv.accounts[1]

		allocated_row.update({"reference_type": against_dt, "reference_name": against_dn})
		if allocated_row.debit_in_account_currency:
			allocated_row.debit_in_account_currency = against_amount if against_amount > 0 else 0
			allocated_row.credit_in_account_currency = abs(against_amount) if against_amount < 0 else 0
		else:
			allocated_row.credit_in_account_currency = against_amount if against_amount > 0 else 0
			allocated_row.debit_in_account_currency = abs(against_amount) if against_amount < 0 else 0

	jv.insert()
	jv.submit()
	return jv


def make_sales_order(party):
	so = frappe.get_doc(frappe.get_test_records('Sales Order')[0])
	so.customer = party.name
	so.insert()
	so.submit()
	return so
