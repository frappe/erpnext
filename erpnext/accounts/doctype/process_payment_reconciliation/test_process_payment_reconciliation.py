# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.process_payment_reconciliation import process_payment_reconciliation as ppr
from erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation import (
	get_pr_instance,
)
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"


class TestProcessPaymentReconciliation(ERPNextTestSuite):
	"""Process Payment Reconciliation validates its accounts against the company,
	moves to Queued on submit, and hands its filters to a Payment Reconciliation run."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_ppr(self, **args):
		args = frappe._dict(args)
		doc = frappe.new_doc("Process Payment Reconciliation")
		doc.company = COMPANY
		doc.party_type = "Customer"
		doc.party = "_Test Customer"
		doc.receivable_payable_account = args.get("receivable_payable_account", "Debtors - _TC")
		doc.bank_cash_account = args.get("bank_cash_account")
		doc.from_invoice_date = args.get("from_invoice_date")
		doc.to_invoice_date = args.get("to_invoice_date")
		return doc

	def other_company_account(self, **extra):
		filters = {"company": "_Test Company 1", "is_group": 0, **extra}
		account = frappe.db.get_value("Account", filters, "name")
		self.assertTrue(account, "need a matching account in _Test Company 1")
		return account

	def test_receivable_account_must_belong_to_company(self):
		doc = self.make_ppr(receivable_payable_account=self.other_company_account(account_type="Receivable"))
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_bank_cash_account_must_belong_to_company(self):
		doc = self.make_ppr(bank_cash_account=self.other_company_account())
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_submit_sets_status_to_queued(self):
		doc = self.make_ppr()
		doc.insert()
		doc.submit()
		self.assertEqual(doc.status, "Queued")

	def test_get_pr_instance_copies_filters_and_caps_limits(self):
		doc = self.make_ppr(from_invoice_date="2026-01-01", to_invoice_date="2026-06-30")
		doc.insert()

		pr = get_pr_instance(doc.name)
		self.assertEqual(pr.company, COMPANY)
		self.assertEqual(pr.party, "_Test Customer")
		self.assertEqual(pr.receivable_payable_account, "Debtors - _TC")
		# old invoice date fields still feed the new single date range
		self.assertEqual(str(pr.from_date), "2026-01-01")
		self.assertEqual(str(pr.to_date), "2026-06-30")
		# the tool run is capped so a single process can't fetch unbounded rows
		self.assertEqual(pr.fetch_limit, 1000)

	def test_get_pr_instance_copies_cost_center(self):
		doc = self.make_ppr()
		doc.cost_center = "_Test Cost Center - _TC"
		doc.insert()

		pr = get_pr_instance(doc.name)
		self.assertEqual(pr.cost_center, "_Test Cost Center - _TC")

	def make_customer(self):
		return frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test PPR Background Customer",
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
			}
		).insert()

	def run_in_place(self, doc):
		doc.insert()
		doc.submit()
		# run the queued steps in place
		ppr.reconcile_based_on_filters(doc.name)
		ppr.fetch_and_allocate(doc.name)
		ppr.reconcile(doc.name)

	def test_background_run_reconciles_invoice_against_credit_note(self):
		"""The log keeps no accounts: the bridge for an invoice / credit note pair gets
		them from the ledger."""
		customer = self.make_customer()
		invoice = create_sales_invoice(customer=customer.name, rate=100)
		credit_note = create_sales_invoice(customer=customer.name, qty=-1, rate=100, do_not_save=True)
		credit_note.is_return = 1
		credit_note.save().submit()

		doc = self.make_ppr()
		doc.party = customer.name
		self.run_in_place(doc)

		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "outstanding_amount"), 0)
		self.assertEqual(frappe.db.get_value("Sales Invoice", credit_note.name, "outstanding_amount"), 0)

	def test_background_run_keeps_the_journal_line(self):
		"""An invoice-side journal line is matched by its row, so the log keeps it."""
		customer = self.make_customer()
		journal = frappe.new_doc("Journal Entry")
		journal.company = COMPANY
		journal.posting_date = nowdate()
		journal.append(
			"accounts",
			{
				"account": "Debtors - _TC",
				"party_type": "Customer",
				"party": customer.name,
				"debit_in_account_currency": 100,
			},
		)
		journal.append(
			"accounts",
			{
				"account": "Sales - _TC",
				"credit_in_account_currency": 100,
				"cost_center": "_Test Cost Center - _TC",
			},
		)
		journal.save().submit()
		create_payment_entry(
			company=COMPANY,
			payment_type="Receive",
			party_type="Customer",
			party=customer.name,
			paid_from="Debtors - _TC",
			paid_to="_Test Bank - _TC",
			paid_amount=100,
		).save().submit()

		doc = self.make_ppr()
		doc.party = customer.name
		self.run_in_place(doc)

		open_amount = frappe.get_all(
			"Payment Ledger Entry",
			filters={"against_voucher_no": journal.name, "delinked": 0},
			fields=[{"SUM": "amount", "as": "total"}],
		)[0].total
		self.assertEqual(open_amount, 0)

	def test_background_run_logs_the_payment_as_reference(self):
		"""A supplier's payment sits in to_receive; the log's reference is still the payment."""
		supplier = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "_Test PPR Background Supplier",
				"supplier_group": "_Test Supplier Group",
			}
		).insert()
		invoice = make_purchase_invoice(supplier=supplier.name, qty=1, rate=100)
		payment = create_payment_entry(
			company=COMPANY,
			payment_type="Pay",
			party_type="Supplier",
			party=supplier.name,
			paid_from="_Test Bank - _TC",
			paid_to="Creditors - _TC",
			paid_amount=100,
		)
		payment.save().submit()

		doc = self.make_ppr(receivable_payable_account="Creditors - _TC")
		doc.party_type = "Supplier"
		doc.party = supplier.name
		self.run_in_place(doc)

		log = frappe.db.get_value("Process Payment Reconciliation Log", {"process_pr": doc.name})
		references = frappe.get_all(
			"Process Payment Reconciliation Log Allocations",
			filters={"parent": log, "invoice_number": invoice.name},
			fields=["reference_type", "reference_name"],
		)
		self.assertEqual(references, [{"reference_type": "Payment Entry", "reference_name": payment.name}])
		self.assertEqual(frappe.db.get_value("Purchase Invoice", invoice.name, "outstanding_amount"), 0)
