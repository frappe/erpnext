# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, nowdate

from erpnext.accounts.doctype.bank_transaction.test_bank_transaction import (
	create_bank_account,
	create_gl_account,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_payment_entry,
	make_payment_order,
)
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_order as _make_payment_order
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.party import get_party_account


class TestPaymentOrder(IntegrationTestCase):
	def setUp(self):
		# generate and use a uniq hash identifier for 'Bank Account' and it's linked GL 'Account' to avoid validation error
		uniq_identifier = frappe.generate_hash(length=10)
		self.gl_account = create_gl_account("_Test Bank " + uniq_identifier)
		self.bank_account = create_bank_account(
			gl_account=self.gl_account, bank_account_name="Checking Account " + uniq_identifier
		)

	def tearDown(self):
		frappe.db.rollback()

	def test_payment_order_creation_against_payment_entry(self):
		purchase_invoice = make_purchase_invoice()
		payment_entry = get_payment_entry(
			"Purchase Invoice", purchase_invoice.name, bank_account=self.gl_account
		)
		payment_entry.reference_no = "_Test_Payment_Order"
		payment_entry.reference_date = getdate()
		payment_entry.party_bank_account = self.bank_account
		payment_entry.insert()
		payment_entry.submit()

		doc = create_payment_order_against_payment_entry(payment_entry, "Payment Entry", self.bank_account)
		reference_doc = doc.get("references")[0]
		self.assertEqual(reference_doc.reference_name, payment_entry.name)
		self.assertEqual(reference_doc.reference_doctype, "Payment Entry")
		self.assertEqual(reference_doc.supplier, "_Test Supplier")
		self.assertEqual(reference_doc.amount, 250)

	def test_payment_order_creation_against_journal_entry(self):
		from erpnext.accounts.doctype.bank_account.test_bank_account import create_bank_account

		pi = make_purchase_invoice()

		create_bank_account(
			account_name="Test Supplier Account", party_type="Supplier", party=pi.supplier, is_default=1
		)
		company_bank_account = create_bank_account(is_company_account=1, is_default=1)

		pr = make_payment_request(
			company=pi.company,
			dt="Purchase Invoice",
			dn=pi.name,
			party_type="Supplier",
			party=pi.supplier,
			mode_of_payment="Wire Transfer",
			return_doc=True,
			submit_doc=True,
		)
		pr_outstanding = pr.outstanding_amount

		po = create_payment_order_against_payment_request(pr, "Payment Request", company_bank_account)

		jv = make_journal_entry_from_payment_order(po, po.party, "Wire Transfer")
		jv.submit()

		pr.reload()
		self.assertEqual(pr.outstanding_amount, 0)
		self.assertEqual(pr.status, "Paid")

		jv.reload()
		jv.cancel()

		pr.reload()
		self.assertEqual(pr.outstanding_amount, pr_outstanding)
		self.assertEqual(pr.status, "Initiated")


def create_payment_order_against_payment_entry(ref_doc, order_type, bank_account):
	payment_order = frappe.get_doc(
		dict(
			doctype="Payment Order",
			company="_Test Company",
			payment_order_type=order_type,
			company_bank_account=bank_account,
		)
	)
	doc = make_payment_order(ref_doc.name, payment_order)
	doc.save()
	doc.submit()
	return doc


def create_payment_order_against_payment_request(ref_doc, order_type, bank_account):
	payment_order = frappe.get_doc(
		dict(
			doctype="Payment Order",
			company="_Test Company",
			payment_order_type=order_type,
			company_bank_account=bank_account,
			account=frappe.db.get_value("Bank Account", bank_account, "account"),
		)
	)
	doc = _make_payment_order(ref_doc.name, payment_order)
	doc.save()
	doc.submit()
	return doc


def make_journal_entry_from_payment_order(doc, supplier, mode_of_payment=None):
	je = frappe.new_doc("Journal Entry")
	je.company = doc.company
	je.payment_order = doc.name
	je.posting_date = nowdate()

	mode_of_payment_type = frappe._dict(frappe.get_all("Mode of Payment", fields=["name", "type"], as_list=1))

	je.voucher_type = "Bank Entry"
	if mode_of_payment and mode_of_payment_type.get(mode_of_payment) == "Cash":
		je.voucher_type = "Cash Entry"

	paid_amt = 0
	party_account = get_party_account("Supplier", supplier, doc.company)
	for d in doc.references:
		if d.supplier == supplier and (not mode_of_payment or mode_of_payment == d.mode_of_payment):
			je.append(
				"accounts",
				{
					"account": party_account,
					"debit_in_account_currency": d.amount,
					"party_type": "Supplier",
					"party": supplier,
					"reference_type": d.reference_doctype,
					"reference_name": d.reference_name,
				},
			)

			paid_amt += d.amount

	je.append("accounts", {"account": doc.account, "credit_in_account_currency": paid_amt})

	je.cheque_no = "1"
	je.cheque_date = nowdate()

	je.flags.ignore_mandatory = True
	je.save()
	return je
