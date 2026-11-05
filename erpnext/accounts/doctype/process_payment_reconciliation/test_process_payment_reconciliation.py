# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from functools import partial
from unittest.mock import patch

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import PaymentReconciliation
from erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation import (
	fetch_and_allocate,
	get_pr_instance,
	pause_job_for_doc,
	reconcile,
	reconcile_based_on_filters,
	trigger_job_for_doc,
	trigger_reconciliation_for_queued_docs,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.doctype.customer.test_customer import make_customer
from erpnext.tests.permission_test_utils import as_user, make_fenced_user
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
		self.assertEqual(str(pr.from_invoice_date), "2026-01-01")
		# the tool run is capped so a single process can't fetch unbounded rows
		self.assertEqual(pr.invoice_limit, 1000)
		self.assertEqual(pr.payment_limit, 1000)

	def test_get_pr_instance_copies_bank_cash_and_cost_center(self):
		doc = self.make_ppr(bank_cash_account="Cash - _TC")
		doc.cost_center = "_Test Cost Center - _TC"
		doc.insert()

		pr = get_pr_instance(doc.name)
		self.assertEqual(pr.bank_cash_account, "Cash - _TC")
		self.assertEqual(pr.cost_center, "_Test Cost Center - _TC")

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

	def test_cancelled_document_stops_its_jobs(self):
		doc = self.make_ppr().insert().submit()
		frappe.get_doc(
			{
				"doctype": "Process Payment Reconciliation Log",
				"process_pr": doc.name,
				"status": "Running",
				"allocated": 1,
				"total_allocations": 0,
				"reconciled_entries": 0,
			}
		).insert()
		doc.cancel()

		with patch("frappe.enqueue") as enqueue:
			reconcile_based_on_filters(doc.name)
			fetch_and_allocate(doc.name)
			reconcile(doc.name)

		enqueue.assert_not_called()
		self.assertEqual(doc.reload().status, "Cancelled")

	def test_only_submitted_documents_can_be_paused_or_started(self):
		draft = self.make_ppr().insert()
		self.assertRaises(frappe.ValidationError, pause_job_for_doc, draft.name)
		self.assertRaises(frappe.ValidationError, trigger_job_for_doc, draft.name)
		self.assertNotEqual(draft.reload().status, "Paused")

		submitted = self.make_ppr().insert().submit()
		pause_job_for_doc(submitted.name)
		self.assertEqual(submitted.reload().status, "Paused")
		# a paused document cannot be paused again
		self.assertRaises(frappe.ValidationError, pause_job_for_doc, submitted.name)

	@ERPNextTestSuite.change_settings(
		"Accounts Settings", {"auto_reconcile_payments": 1, "reconciliation_queue_size": 5}
	)
	def test_queued_documents_wait_for_a_running_one(self):
		module = "erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation"
		running = self.make_ppr().insert().submit()
		running.db_set("status", "Running")
		waiting = self.make_ppr().insert().submit()

		other_customer = make_customer("_Test Reconciliation Queue Order")
		first = self.make_ppr()
		first.party = other_customer
		first.insert().submit()
		second = self.make_ppr()
		second.party = other_customer
		second.insert().submit()

		with (
			patch(f"{module}.is_scheduler_inactive", return_value=False),
			patch(f"{module}.trigger_job_for_doc") as trigger,
		):
			trigger_reconciliation_for_queued_docs()

		triggered = [call.args[0] for call in trigger.call_args_list]
		self.assertNotIn(waiting.name, triggered)
		# the oldest of two documents with the same filters goes first
		self.assertIn(first.name, triggered)
		self.assertNotIn(second.name, triggered)
