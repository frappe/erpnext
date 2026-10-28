# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from functools import partial
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import PaymentReconciliation
from erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation import (
	fetch_and_allocate,
	get_pr_instance,
	reconcile,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.doctype.customer.test_customer import make_customer
from erpnext.tests.permission_test_utils import as_user, make_fenced_user

COMPANY = "_Test Company"


class TestProcessPaymentReconciliation(FrappeTestCase):
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

	def test_log_permissions_allow_cleanup(self):
		for role in ("Accounts User", "Accounts Manager"):
			user = make_fenced_user("reconciliation-log@example.com", [role])
			doc = self.make_ppr().insert().submit()
			log = frappe.get_doc(
				{"doctype": "Process Payment Reconciliation Log", "process_pr": doc.name}
			).insert()
			with self.subTest(role=role), as_user(user):
				log.check_permission("read")
				for permission in ("create", "write", "share"):
					with self.assertRaises(frappe.PermissionError):
						log.check_permission(permission)
				doc.cancel()
				frappe.delete_doc(log.doctype, log.name)
				frappe.delete_doc(doc.doctype, doc.name)
				self.assertFalse(frappe.db.exists(log.doctype, log.name))
				self.assertFalse(frappe.db.exists(doc.doctype, doc.name))

	def test_worker_rejects_allocation_after_invoice_balance_changes(self):
		customer = make_customer("_Test Reconciliation Stale Balance")
		invoice = create_sales_invoice(customer=customer, qty=1, rate=600)
		advance = create_payment_entry(
			payment_type="Receive",
			party_type="Customer",
			party=customer,
			paid_from="Debtors - _TC",
			paid_to="Cash - _TC",
			paid_amount=1000,
			save=True,
			submit=True,
		)
		doc = self.make_ppr()
		doc.party = customer
		doc.insert().submit()
		log = frappe.get_doc(
			{"doctype": "Process Payment Reconciliation Log", "process_pr": doc.name}
		).insert()
		with patch("frappe.enqueue"):
			fetch_and_allocate(doc.name)
		log.reload()
		self.assertEqual(len(log.allocations), 1)
		self.assertEqual(log.allocations[0].invoice_number, invoice.name)
		self.assertEqual(log.allocations[0].reference_name, advance.name)
		self.assertEqual(log.allocations[0].allocated_amount, 600)

		payment = get_payment_entry(invoice.doctype, invoice.name, bank_account="Cash - _TC")
		payment.paid_amount = payment.received_amount = 200
		payment.references[0].allocated_amount = 200
		payment.insert().submit()
		self.assertEqual(invoice.reload().outstanding_amount, 400)

		# Keep the fixtures when the worker rolls back the failed batch.
		frappe.db.savepoint("before_reconciliation_batch")
		rollback = partial(frappe.db.rollback, save_point="before_reconciliation_batch")
		with (
			patch.object(frappe.db, "rollback", side_effect=rollback),
			patch("frappe.enqueue"),
			patch.object(PaymentReconciliation, "reconcile_allocations") as reconcile_allocations,
		):
			reconcile(doc.name)
			reconcile_allocations.assert_not_called()

		log.reload()
		self.assertEqual(log.status, "Failed")
		self.assertIn("invoice outstanding amount 400", log.error_log)
		self.assertEqual(log.reconciled_entries, 0)
		self.assertFalse(log.allocations[0].reconciled)
		self.assertEqual(invoice.reload().outstanding_amount, 400)
		self.assertEqual(advance.reload().unallocated_amount, 1000)

	def test_worker_reconciles_queued_invoice_outside_selection_limit(self):
		customer = make_customer("_Test Reconciliation Invoice Limit")
		invoice = create_sales_invoice(customer=customer, qty=1, rate=600)
		advance = create_payment_entry(
			payment_type="Receive",
			party_type="Customer",
			party=customer,
			paid_from="Debtors - _TC",
			paid_to="Cash - _TC",
			paid_amount=600,
			save=True,
			submit=True,
		)
		doc = self.make_ppr()
		doc.party = customer
		doc.insert().submit()
		log = frappe.get_doc(
			{"doctype": "Process Payment Reconciliation Log", "process_pr": doc.name}
		).insert()
		with patch("frappe.enqueue"):
			fetch_and_allocate(doc.name)
		self.assertEqual(log.reload().allocations[0].invoice_number, invoice.name)

		backdated_invoice = create_sales_invoice(
			customer=customer, qty=1, rate=600, posting_date=add_days(today(), -1)
		)
		pr = get_pr_instance(doc.name)
		# Reproduce the selection cap with two invoices instead of creating 1,001.
		pr.invoice_limit = 1
		pr.get_unreconciled_entries()
		self.assertEqual([row.invoice_number for row in pr.invoices], [backdated_invoice.name])

		frappe.db.savepoint("before_reconciliation_batch")
		rollback = partial(frappe.db.rollback, save_point="before_reconciliation_batch")
		with (
			patch.object(frappe.db, "rollback", side_effect=rollback),
			patch("frappe.enqueue"),
			patch(
				"erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.get_pr_instance",
				return_value=pr,
			),
		):
			reconcile(doc.name)

		log.reload()
		self.assertFalse(log.error_log)
		self.assertEqual(log.reconciled_entries, 1)
		self.assertTrue(log.allocations[0].reconciled)
		self.assertEqual([row.invoice_number for row in pr.invoices], [invoice.name])
		self.assertEqual(invoice.reload().outstanding_amount, 0)
		self.assertEqual(advance.reload().unallocated_amount, 0)
		self.assertEqual(backdated_invoice.reload().outstanding_amount, 600)
