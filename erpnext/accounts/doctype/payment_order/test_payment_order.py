# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.utils import getdate

from erpnext.accounts.doctype.bank_transaction.test_bank_transaction import (
	create_bank_account,
	create_gl_account,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_payment_entry,
	make_payment_order,
)
from erpnext.accounts.doctype.payment_order.payment_order import make_payment_records
from erpnext.accounts.doctype.payment_request.payment_request import (
	make_payment_order as make_payment_order_from_payment_request,
)
from erpnext.accounts.doctype.payment_request.payment_request import (
	make_payment_request,
)
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.tests.utils import ERPNextTestSuite


class TestPaymentOrder(ERPNextTestSuite):
	def setUp(self):
		# generate and use a uniq hash identifier for 'Bank Account' and it's linked GL 'Account' to avoid validation error
		uniq_identifier = frappe.generate_hash(length=10)
		self.gl_account = create_gl_account("_Test Bank " + uniq_identifier)
		self.bank_account = create_bank_account(
			gl_account=self.gl_account, bank_account_name="Checking Account " + uniq_identifier
		)
		frappe.db.set_value(
			"Bank Account", self.bank_account, {"is_company_account": 1, "company": "_Test Company"}
		)

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

	def test_payment_order_from_payment_entry_uses_its_own_naming_series(self):
		payment_entry = self.make_payment_entry()

		payment_order = make_payment_order(payment_entry.name)
		payment_order.company_bank_account = self.bank_account
		payment_order.insert()

		self.assertEqual(payment_order.naming_series, "PMO-")
		self.assertTrue(payment_order.name.startswith("PMO-"))

	def test_payment_order_references_must_be_submitted_and_not_in_another_order(self):
		payment_entry = self.make_payment_entry()
		create_payment_order_against_payment_entry(payment_entry, "Payment Entry", self.bank_account)

		second_order = make_payment_order(payment_entry.name)
		second_order.company_bank_account = self.bank_account
		self.assertRaisesRegex(frappe.ValidationError, "is already in Payment Order", second_order.insert)

		draft_payment_request = self.make_payment_request(submit_doc=0)
		payment_order = make_payment_order_from_payment_request(draft_payment_request.name)
		payment_order.company_bank_account = self.bank_account
		self.assertRaisesRegex(frappe.ValidationError, "must be submitted", payment_order.insert)

	def test_payment_order_keeps_payment_request_status(self):
		payment_request = self.make_payment_request()
		payment_entry = payment_request.create_payment_entry(submit=False)
		payment_entry.paid_amount = payment_entry.received_amount = 400
		payment_entry.references[0].allocated_amount = 400
		payment_entry.submit()

		payment_order = make_payment_order_from_payment_request(payment_request.name)
		payment_order.company_bank_account = self.bank_account
		payment_order.insert()
		payment_order.submit()
		self.assertEqual(payment_order.references[0].amount, 600)
		self.assertEqual(
			frappe.db.get_value("Payment Request", payment_request.name, "status"), "Payment Ordered"
		)

		payment_order.cancel()
		self.assertEqual(
			frappe.db.get_value("Payment Request", payment_request.name, "status"), "Partially Paid"
		)

		payment_request.reload()
		payment_request.create_payment_entry()
		paid_order = make_payment_order_from_payment_request(payment_request.name)
		paid_order.company_bank_account = self.bank_account
		self.assertRaisesRegex(frappe.ValidationError, "is already paid", paid_order.insert)

	def test_journal_entry_from_payment_order_updates_payment_request(self):
		payment_request = self.make_payment_request()
		payment_order = make_payment_order_from_payment_request(payment_request.name)
		payment_order.company_bank_account = self.bank_account
		payment_order.insert()
		payment_order.submit()

		make_payment_records(payment_order.name, "_Test Supplier")
		self.assertRaisesRegex(
			frappe.ValidationError,
			"Journal Entries are already created",
			make_payment_records,
			payment_order.name,
			"_Test Supplier",
		)

		journal_entry = frappe.get_doc(
			"Journal Entry", frappe.db.get_value("Journal Entry", {"payment_order": payment_order.name})
		)
		journal_entry.cheque_no = "_Test_Payment_Order"
		journal_entry.cheque_date = getdate()
		journal_entry.submit()
		self.assertEqual(
			frappe.db.get_value("Payment Request", payment_request.name, ["status", "outstanding_amount"]),
			("Paid", 0),
		)

		journal_entry.cancel()
		self.assertEqual(
			frappe.db.get_value("Payment Request", payment_request.name, ["status", "outstanding_amount"]),
			("Payment Ordered", 1000),
		)
		self.assertIsNone(
			frappe.db.get_value(
				"Payment Order Reference", {"parent": payment_order.name}, "payment_reference"
			)
		)

		make_payment_records(payment_order.name, "_Test Supplier")
		draft_journal_entry = frappe.db.get_value(
			"Payment Order Reference", {"parent": payment_order.name}, "payment_reference"
		)
		frappe.delete_doc("Journal Entry", draft_journal_entry)
		self.assertIsNone(
			frappe.db.get_value(
				"Payment Order Reference", {"parent": payment_order.name}, "payment_reference"
			)
		)

	def make_payment_request(self, submit_doc=1, rate=1000):
		purchase_invoice = make_purchase_invoice(qty=1, rate=rate)
		if not frappe.db.exists("Bank Account", {"party_type": "Supplier", "party": "_Test Supplier"}):
			frappe.get_doc(
				{
					"doctype": "Bank Account",
					"account_name": "_Test Supplier Account",
					"bank": "Citi Bank",
					"party_type": "Supplier",
					"party": "_Test Supplier",
					"is_default": 1,
				}
			).insert()

		return make_payment_request(
			dt="Purchase Invoice",
			dn=purchase_invoice.name,
			party_type="Supplier",
			party="_Test Supplier",
			mute_email=1,
			submit_doc=submit_doc,
			return_doc=1,
		)

	def make_payment_entry(self):
		purchase_invoice = make_purchase_invoice()
		payment_entry = get_payment_entry(
			"Purchase Invoice", purchase_invoice.name, bank_account=self.gl_account
		)
		payment_entry.reference_no = "_Test_Payment_Order"
		payment_entry.reference_date = getdate()
		payment_entry.party_bank_account = self.bank_account
		payment_entry.insert()
		payment_entry.submit()
		return payment_entry


def create_payment_order_against_payment_entry(ref_doc, order_type, bank_account):
	payment_order = frappe.get_doc(
		doctype="Payment Order",
		company="_Test Company",
		payment_order_type=order_type,
		company_bank_account=bank_account,
	)
	doc = make_payment_order(ref_doc.name, payment_order)
	doc.save()
	doc.submit()
	return doc
