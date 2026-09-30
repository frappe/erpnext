# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe import qb
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, nowdate, today

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger import (
	_lock_vouchers,
	_record_repost_failure,
	_repost_allowed_hook_doctypes,
	_repost_job_id,
	_repost_vouchers,
	repost,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import get_gl_entries, make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite

REPOST_MODULE = "erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger"
SIMULATED_FAILURE = "Simulated repost failure"


class TestRepostAccountingLedger(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value("Selling Settings", "validate_selling_price", 0)
		update_repost_settings()

	def make_invoice(self, **kwargs):
		return create_sales_invoice(
			item="_Test Item",
			company="_Test Company",
			customer="_Test Customer",
			debit_to="Debtors - _TC",
			parent_cost_center="Main - _TC",
			cost_center="Main - _TC",
			rate=100,
			**kwargs,
		)

	def make_invoice_and_payment(self):
		si = self.make_invoice()
		pe = get_payment_entry(si.doctype, si.name)
		pe.save().submit()
		return si, pe

	def create_repost_doc(self, vouchers, delete_cancelled_entries=False, submit=False):
		ral = frappe.new_doc("Repost Accounting Ledger")
		ral.company = "_Test Company"
		ral.delete_cancelled_entries = delete_cancelled_entries
		for voucher in vouchers:
			ral.append("vouchers", {"voucher_type": voucher.doctype, "voucher_no": voucher.name})

		ral.save()
		if submit:
			ral.submit()
			ral.reload()
		return ral

	@contextmanager
	def patched_repost(self, fail_for=()):
		"""Yield the vouchers handed over to `_repost_vouchers`, failing the given types."""
		reposted = []

		def repost_voucher(doc, delete_cancelled_entries):
			reposted.append(doc.name)
			if doc.doctype in fail_for:
				frappe.throw(SIMULATED_FAILURE)
			_repost_vouchers(doc, delete_cancelled_entries)

		with patch(f"{REPOST_MODULE}._repost_vouchers", new=repost_voucher):
			yield reposted

	def make_period_closing_voucher(self):
		fy = get_fiscal_year(today(), company="_Test Company")
		pcv = frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": today(),
				"period_start_date": fy[1],
				"period_end_date": today(),
				"company": "_Test Company",
				"fiscal_year": fy[0],
				"cost_center": "Main - _TC",
				"closing_account_head": "Retained Earnings - _TC",
				"remarks": "test",
			}
		)
		return pcv.save().submit()

	def get_gl_totals(self, voucher_no, is_cancelled=0):
		gl = qb.DocType("GL Entry")
		return (
			qb.from_(gl)
			.select(Sum(gl.debit).as_("debit"), Sum(gl.credit).as_("credit"))
			.where((gl.voucher_no == voucher_no) & (gl.is_cancelled == is_cancelled))
			.run()
		)[0]

	def test_01_basic_functions(self):
		si = self.make_invoice()

		preq = frappe.get_doc(
			make_payment_request(
				dt=si.doctype,
				dn=si.name,
				payment_request_type="Inward",
				party_type="Customer",
				party=si.customer,
			)
		)
		preq.save().submit()

		# Test Validation Error
		ral = frappe.new_doc("Repost Accounting Ledger")
		ral.company = "_Test Company"
		ral.delete_cancelled_entries = True
		ral.append("vouchers", {"voucher_type": si.doctype, "voucher_no": si.name})
		ral.append(
			"vouchers", {"voucher_type": preq.doctype, "voucher_no": preq.name}
		)  # this should throw validation error
		self.assertRaises(frappe.ValidationError, ral.save)
		ral.vouchers.pop()
		preq.cancel()
		preq.delete()

		pe = get_payment_entry(si.doctype, si.name)
		pe.save().submit()
		ral.append("vouchers", {"voucher_type": pe.doctype, "voucher_no": pe.name})
		ral.save()

		# manually set an incorrect debit amount in DB
		gle = frappe.db.get_all("GL Entry", filters={"voucher_no": si.name, "account": "Debtors - _TC"})
		frappe.db.set_value("GL Entry", gle[0], "debit", 90)

		# Assert incorrect ledger balance
		self.assertNotEqual(self.get_gl_totals(si.name), (100, 100))

		# Submit repost document
		ral.save().submit()

		# Ledger should reflect correct amount post repost
		self.assertEqual(self.get_gl_totals(si.name), (100, 100))

	def test_02_deferred_accounting_valiations(self):
		si = self.make_invoice(do_not_submit=True)
		si.items[0].enable_deferred_revenue = True
		si.items[0].deferred_revenue_account = "Deferred Revenue - _TC"
		si.items[0].service_start_date = nowdate()
		si.items[0].service_end_date = add_days(nowdate(), 90)
		si.save().submit()

		self.assertRaises(frappe.ValidationError, self.create_repost_doc, [si])

	@ERPNextTestSuite.change_settings("Accounts Settings", {"delete_linked_ledger_entries": 1})
	def test_04_pcv_validation(self):
		# Clear old GL entries so PCV can be submitted.
		gl = frappe.qb.DocType("GL Entry")
		qb.from_(gl).delete().where(gl.company == "_Test Company").run()

		si = self.make_invoice()
		pcv = self.make_period_closing_voucher()

		self.assertRaises(frappe.ValidationError, self.create_repost_doc, [si])

		pcv.reload()
		pcv.cancel()
		pcv.delete()

	def test_03_deletion_flag_and_preview_function(self):
		si, pe = self.make_invoice_and_payment()

		# with deletion flag set
		self.create_repost_doc([si, pe], delete_cancelled_entries=True, submit=True)

		self.assertIsNone(frappe.db.exists("GL Entry", {"voucher_no": si.name, "is_cancelled": 1}))
		self.assertIsNone(frappe.db.exists("GL Entry", {"voucher_no": pe.name, "is_cancelled": 1}))

	def test_05_without_deletion_flag(self):
		si, pe = self.make_invoice_and_payment()

		# without deletion flag set
		self.create_repost_doc([si, pe], submit=True)

		self.assertIsNotNone(frappe.db.exists("GL Entry", {"voucher_no": si.name, "is_cancelled": 1}))
		self.assertIsNotNone(frappe.db.exists("GL Entry", {"voucher_no": pe.name, "is_cancelled": 1}))

	def test_06_repost_purchase_receipt(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		if not frappe.db.set_value("Company", "_Test Company", "service_expense_account"):
			frappe.db.set_value(
				"Company", "_Test Company", "service_expense_account", "Marketing Expenses - _TC"
			)

		provisional_account = create_account(
			account_name="Provision Account",
			parent_account="Current Liabilities - _TC",
			company="_Test Company",
		)

		another_provisional_account = create_account(
			account_name="Another Provision Account",
			parent_account="Current Liabilities - _TC",
			company="_Test Company",
		)

		company = frappe.get_doc("Company", "_Test Company")
		company.enable_provisional_accounting_for_non_stock_items = 1
		company.default_provisional_account = provisional_account
		company.save()

		test_cc = company.cost_center
		default_expense_account = company.service_expense_account

		item = make_item(properties={"is_stock_item": 0})

		pr = make_purchase_receipt(company="_Test Company", item_code=item.name, rate=1000.0, qty=1.0)
		pr_gl_entries = get_gl_entries(pr.doctype, pr.name, skip_cancelled=True)
		expected_pr_gles = [
			{"account": provisional_account, "debit": 0.0, "credit": 1000.0, "cost_center": test_cc},
			{"account": default_expense_account, "debit": 1000.0, "credit": 0.0, "cost_center": test_cc},
		]
		self.assertEqual(expected_pr_gles, pr_gl_entries)

		# change the provisional account
		frappe.db.set_value(
			"Purchase Receipt Item",
			pr.items[0].name,
			"provisional_expense_account",
			another_provisional_account,
		)

		repost_doc = self.create_repost_doc([pr], delete_cancelled_entries=True, submit=True)

		pr_gles_after_repost = get_gl_entries(pr.doctype, pr.name, skip_cancelled=True)
		expected_pr_gles_after_repost = [
			{"account": default_expense_account, "debit": 1000.0, "credit": 0.0, "cost_center": test_cc},
			{"account": another_provisional_account, "debit": 0.0, "credit": 1000.0, "cost_center": test_cc},
		]
		self.assertEqual(len(pr_gles_after_repost), len(expected_pr_gles_after_repost))
		self.assertEqual(expected_pr_gles_after_repost, pr_gles_after_repost)

		# teardown
		repost_doc.cancel()
		repost_doc.delete()

		pr.reload()
		pr.cancel()

		company.enable_provisional_accounting_for_non_stock_items = 0
		company.default_provisional_account = None
		company.save()

	def test_07_voucher_validations(self):
		submitted_si = self.make_invoice()
		draft_si = self.make_invoice(do_not_submit=True)
		cancelled_si = self.make_invoice()
		cancelled_si.cancel()

		for vouchers, exception, message in (
			([], frappe.ValidationError, "Add atleast one voucher"),
			([submitted_si, submitted_si], frappe.ValidationError, "Duplicate vouchers found"),
			([draft_si], frappe.ValidationError, f"not submitted.*{draft_si.name}"),
			# cancelled vouchers don't make it past link validation
			([cancelled_si], frappe.CancelledLinkError, "Cannot link cancelled document"),
		):
			with self.subTest(vouchers=[x.name for x in vouchers]):
				self.assertRaisesRegex(exception, message, self.create_repost_doc, vouchers)

		self.create_repost_doc([submitted_si])

	def test_08_voucher_count_limit(self):
		si, pe = self.make_invoice_and_payment()
		another_si = self.make_invoice()

		with patch(f"{REPOST_MODULE}.MAX_VOUCHERS_PER_REPOST", 2):
			self.create_repost_doc([si, pe])
			self.assertRaisesRegex(
				frappe.ValidationError,
				"Cannot repost more than 2 vouchers",
				self.create_repost_doc,
				[si, pe, another_si],
			)

	def test_09_status_lifecycle(self):
		si, pe = self.make_invoice_and_payment()

		ral = self.create_repost_doc([si, pe])
		self.assertEqual(ral.status, "")

		ral.submit()
		ral.reload()

		self.assertEqual(ral.status, "Completed")
		self.assertFalse(ral.error_log)
		for voucher in ral.vouchers:
			self.assertEqual(voucher.status, "Reposted")
			self.assertFalse(voucher.traceback)

		ral.cancel()
		ral.reload()
		self.assertEqual(ral.status, "Cancelled")

		discarded = self.create_repost_doc([si])
		discarded.discard()
		discarded.reload()
		self.assertEqual(discarded.status, "Cancelled")

	def test_10_start_repost_guards(self):
		si = self.make_invoice()
		ral = self.create_repost_doc([si])

		self.assertRaisesRegex(frappe.ValidationError, "only for submitted document", ral.start_repost)

		ral.submit()
		ral.reload()
		self.assertRaisesRegex(
			frappe.ValidationError, "cannot be started when status is Completed", ral.start_repost
		)

		# a document left behind by a worker that died mid-repost
		ral.db_set("status", "In Progress")

		with patch(f"{REPOST_MODULE}.is_job_enqueued", return_value=True):
			self.assertRaisesRegex(
				frappe.ValidationError, "still in progress in background", ral.start_repost
			)
			self.assertRaisesRegex(frappe.ValidationError, "still in progress in background", ral.cancel)

		# `cancel` flips docstatus in memory before running `before_cancel`
		ral.reload()

		with patch(f"{REPOST_MODULE}.is_job_enqueued", return_value=False):
			# the job is gone, so `In Progress` must not keep the document stuck
			ral.start_repost()

		ral.reload()
		self.assertEqual(ral.status, "Completed")

	def test_11_repost_job_is_tied_to_the_document(self):
		si = self.make_invoice()
		ral = self.create_repost_doc([si], submit=True)
		ral.db_set("status", "Failed")

		with patch(f"{REPOST_MODULE}.frappe.enqueue") as enqueue:
			ral.start_repost()

		kwargs = enqueue.call_args.kwargs
		self.assertEqual(kwargs["repost_doc_name"], ral.name)
		self.assertEqual(kwargs["job_id"], _repost_job_id(ral.name))
		# a second start cannot queue a second job for the same document
		self.assertTrue(kwargs["deduplicate"])

	def test_12_voucher_failures_are_isolated_and_retried(self):
		si, pe = self.make_invoice_and_payment()
		pe_gl_entries = frappe.db.count("GL Entry", {"voucher_no": pe.name})

		# the deletion flag drops the existing entries before reposting them
		ral = self.create_repost_doc([si, pe], delete_cancelled_entries=True)
		with self.patched_repost(fail_for=["Payment Entry"]):
			ral.submit()

		ral.reload()
		self.assertEqual(ral.status, "Partially Reposted")

		si_row, pe_row = ral.vouchers
		self.assertEqual((si_row.status, pe_row.status), ("Reposted", "Failed"))
		self.assertFalse(si_row.traceback)
		self.assertIn(SIMULATED_FAILURE, pe_row.traceback)

		# the failed voucher is rolled back to its savepoint, so its entries are back
		self.assertEqual(frappe.db.count("GL Entry", {"voucher_no": pe.name}), pe_gl_entries)

		# a retry only picks up the vouchers that are not reposted yet, and leaves the rest
		# alone entirely: they are not locked or loaded either
		with (
			patch(f"{REPOST_MODULE}._lock_vouchers", side_effect=_lock_vouchers) as lock_vouchers,
			self.patched_repost() as retried,
		):
			ral.start_repost()

		self.assertEqual(retried, [pe.name])
		self.assertEqual([x.voucher_no for x in lock_vouchers.call_args.args[0]], [pe.name])

		ral.reload()
		self.assertEqual(ral.status, "Completed")
		for voucher in ral.vouchers:
			self.assertEqual(voucher.status, "Reposted")
			self.assertFalse(voucher.traceback)

	def test_13_status_of_a_run_that_could_not_finish(self):
		si, pe = self.make_invoice_and_payment()

		ral = self.create_repost_doc([si, pe])
		with self.patched_repost(fail_for=["Payment Entry"]):
			ral.submit()

		ral.reload()

		# the job dies after the loop committed the invoice, e.g. killed or timed out
		try:
			frappe.throw(SIMULATED_FAILURE)
		except frappe.ValidationError:
			_record_repost_failure(ral)

		ral.reload()

		# progress already committed must not be reported as a total failure
		self.assertEqual(ral.status, "Partially Reposted")
		self.assertIn(SIMULATED_FAILURE, ral.error_log)
		self.assertTrue(
			frappe.db.exists("Error Log", {"reference_doctype": ral.doctype, "reference_name": ral.name})
		)

	@ERPNextTestSuite.change_settings("Accounts Settings", {"delete_linked_ledger_entries": 1})
	def test_14_period_closed_after_the_repost_was_started(self):
		gl = qb.DocType("GL Entry")
		qb.from_(gl).delete().where(gl.company == "_Test Company").run()

		si = self.make_invoice()
		ral = self.create_repost_doc([si], submit=True)
		ral.db_set("status", "Failed")
		ral.vouchers[0].db_set("status", "Pending")

		# the period is closed between the repost being started and the job running
		self.make_period_closing_voucher()

		gl_entries = frappe.db.count("GL Entry", {"voucher_no": si.name})
		self.assertRaisesRegex(frappe.ValidationError, "Closed fiscal year", repost, ral.name, commit=False)

		ral.reload()
		self.assertEqual(ral.status, "Failed")
		self.assertIn("Closed fiscal year", ral.error_log)

		# the ledger is left exactly as it was
		self.assertEqual(frappe.db.count("GL Entry", {"voucher_no": si.name}), gl_entries)
		self.assertEqual(ral.vouchers[0].status, "Pending")

	def test_15_failed_repost_skips_cancelled_voucher(self):
		si = self.make_invoice()

		ral = self.create_repost_doc([si])
		with self.patched_repost(fail_for=["Sales Invoice"]):
			ral.submit()

		ral.reload()
		self.assertEqual(ral.status, "Failed")

		si.reload()
		si.cancel()

		ral.start_repost()
		ral.reload()

		# nothing was reposted, but there is nothing left to repost either
		self.assertEqual(ral.status, "Completed")
		self.assertEqual(ral.vouchers[0].status, "Skipped")
		self.assertFalse(ral.vouchers[0].traceback)

	def test_16_concurrent_repost_is_blocked_by_voucher_lock(self):
		si, pe = self.make_invoice_and_payment()
		ral = self.create_repost_doc([si, pe])

		# a concurrent repost holding the lock on the second voucher
		locked_pe = frappe.get_doc(pe.doctype, pe.name)
		locked_pe.lock()
		try:
			self.assertRaises(frappe.DocumentLockedError, ral.submit)

			# vouchers locked before the failure are released again
			self.assertFalse(frappe.get_doc(si.doctype, si.name).is_locked)
		finally:
			locked_pe.unlock()

	def test_17_journal_entry_repost(self):
		je = make_journal_entry("_Test Bank - _TC", "_Test Cash - _TC", 500, submit=True)
		je = frappe.get_doc("Journal Entry", je.name)

		self.assertEqual(self.get_gl_totals(je.name), (500.0, 500.0))

		# without the deletion flag the 2 original entries are marked as cancelled,
		# along with the 2 reverse entries booked against them
		for delete_cancelled_entries, cancelled_entries in ((False, 4), (True, 0)):
			with self.subTest(delete_cancelled_entries=delete_cancelled_entries):
				ral = self.create_repost_doc(
					[je], delete_cancelled_entries=delete_cancelled_entries, submit=True
				)

				self.assertEqual(ral.status, "Completed")
				self.assertEqual(self.get_gl_totals(je.name), (500.0, 500.0))
				self.assertEqual(
					frappe.db.count("GL Entry", {"voucher_no": je.name, "is_cancelled": 1}),
					cancelled_entries,
				)

	def test_18_hook_allowed_doctype_repost(self):
		class VoucherWithCancelArg:
			doctype = "Test Repost Voucher"
			name = "TRV-00001"

			def __init__(self):
				self.calls = []

			def make_gl_entries(self, cancel=0):
				self.calls.append(cancel)

		class VoucherWithoutCancelArg(VoucherWithCancelArg):
			def make_gl_entries(self):
				self.calls.append("repost")

		# vouchers that can reverse their own entries are asked to do so first
		doc = VoucherWithCancelArg()
		_repost_allowed_hook_doctypes(doc, delete_cancelled_entries=False)
		self.assertEqual(doc.calls, [1, 0])

		# nothing to reverse when the old entries are deleted
		doc = VoucherWithCancelArg()
		_repost_allowed_hook_doctypes(doc, delete_cancelled_entries=True)
		self.assertEqual(doc.calls, [0])

		# the rest fall back to the generic reversal
		doc = VoucherWithoutCancelArg()
		with patch("erpnext.accounts.general_ledger.make_reverse_gl_entries") as make_reverse_gl_entries:
			_repost_allowed_hook_doctypes(doc, delete_cancelled_entries=False)

		make_reverse_gl_entries.assert_called_once_with(voucher_type=doc.doctype, voucher_no=doc.name)
		self.assertEqual(doc.calls, ["repost"])


def update_repost_settings():
	allowed_types = [
		"Sales Invoice",
		"Purchase Invoice",
		"Payment Entry",
		"Journal Entry",
		"Purchase Receipt",
	]
	settings = frappe.get_doc("Accounts Settings")
	for _type in allowed_types:
		if _type not in [x.document_type for x in settings.repost_allowed_types]:
			settings.append("repost_allowed_types", {"document_type": _type})
	settings.save()
