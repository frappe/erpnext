# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe import qb

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
from erpnext.accounts.doctype.cost_center_allocation.test_cost_center_allocation import (
	create_cost_center_allocation,
)
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.repost_payment_ledger.repost_payment_ledger import start_payment_ledger_repost
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.utils import _delete_pl_entries
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
REPOST_MODULE = "erpnext.accounts.doctype.repost_payment_ledger.repost_payment_ledger"


class TestRepostPaymentLedger(ERPNextTestSuite):
	"""Repost Payment Ledger auto-selects submitted vouchers on/after a cutoff date
	(unless rows are added manually) and queues them for a ledger rebuild."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_repost(self, **args):
		args = frappe._dict(args)
		doc = frappe.new_doc("Repost Payment Ledger")
		doc.company = COMPANY
		doc.posting_date = args.get("posting_date", "2026-06-01")
		doc.voucher_type = args.get("voucher_type", "Sales Invoice")
		doc.add_manually = args.get("add_manually", 0)
		return doc

	def submit_repost(self, vouchers):
		doc = self.make_repost(add_manually=1)
		for voucher in vouchers:
			doc.append("repost_vouchers", {"voucher_type": voucher.doctype, "voucher_no": voucher.name})
		# the tests run the background job directly
		with patch(f"{REPOST_MODULE}.execute_repost_payment_ledger"):
			doc.save().submit()
		return doc

	def get_ple(self, voucher_no):
		ple = qb.DocType("Payment Ledger Entry")
		return (
			qb.from_(ple)
			.select(ple.account, ple.cost_center, ple.against_voucher_no, ple.amount)
			.where((ple.voucher_no == voucher_no) & (ple.delinked == 0))
			.orderby(ple.account, ple.cost_center, ple.against_voucher_no, ple.amount)
			.run(as_dict=True)
		)

	def get_repost_status(self, doc):
		return frappe.db.get_value(doc.doctype, doc.name, "repost_status")

	def test_loads_submitted_vouchers_on_or_after_cutoff(self):
		after_cutoff = create_sales_invoice(company=COMPANY, posting_date="2026-06-15", rate=100, qty=1)
		on_cutoff = create_sales_invoice(company=COMPANY, posting_date="2026-06-01", rate=100, qty=1)
		before_cutoff = create_sales_invoice(company=COMPANY, posting_date="2026-01-15", rate=100, qty=1)

		doc = self.make_repost(posting_date="2026-06-01", voucher_type="Sales Invoice")
		doc.save()  # before_validate loads the vouchers and sets status

		loaded = {v.voucher_no for v in doc.repost_vouchers}
		self.assertIn(after_cutoff.name, loaded)
		# the filter is >= so an invoice posted exactly on the cutoff is included
		self.assertIn(on_cutoff.name, loaded)
		self.assertNotIn(before_cutoff.name, loaded)
		self.assertEqual(doc.repost_status, "Queued")

	def test_add_manually_preserves_user_rows(self):
		# manually add a BEFORE-cutoff invoice (which the filter would never load) while a
		# matching after-cutoff invoice also exists. If auto-loading wrongly ran it would
		# drop the manual row and pull the after-cutoff one, so this distinguishes the modes.
		manual_si = create_sales_invoice(company=COMPANY, posting_date="2026-01-15", rate=100, qty=1)
		create_sales_invoice(company=COMPANY, posting_date="2026-06-15", rate=100, qty=1)

		doc = self.make_repost(add_manually=1, posting_date="2026-06-01")
		doc.append("repost_vouchers", {"voucher_type": "Sales Invoice", "voucher_no": manual_si.name})
		doc.save()

		rows = [(v.voucher_type, v.voucher_no) for v in doc.repost_vouchers]
		self.assertEqual(rows, [("Sales Invoice", manual_si.name)])

	def test_add_manually_refuses_draft_vouchers(self):
		draft_si = create_sales_invoice(company=COMPANY, rate=100, qty=1, do_not_submit=True)

		doc = self.make_repost(add_manually=1)
		doc.append("repost_vouchers", {"voucher_type": "Sales Invoice", "voucher_no": draft_si.name})
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_cancelled_voucher_does_not_block_the_repost(self):
		cancelled_si = create_sales_invoice(company=COMPANY, rate=100, qty=1)
		si = create_sales_invoice(company=COMPANY, rate=100, qty=1)
		repost = self.submit_repost([cancelled_si, si])

		cancelled_si.cancel()
		_delete_pl_entries(si.doctype, si.name)
		start_payment_ledger_repost(repost.name)

		self.assertEqual(self.get_repost_status(repost), "Completed")
		self.assertEqual(sum(d.amount for d in self.get_ple(si.name)), 100)

	def test_repost_keeps_advance_allocation_in_separate_party_account(self):
		advance_account = create_account(
			parent_account="Current Assets - _TC",
			account_name="Advances Received",
			company=COMPANY,
			account_type="Receivable",
		)
		frappe.db.set_value(
			"Company",
			COMPANY,
			{
				"book_advance_payments_in_separate_party_account": 1,
				"default_advance_received_account": advance_account,
			},
		)
		pe = create_payment_entry(
			party_type="Customer",
			party="_Test Customer",
			payment_type="Receive",
			paid_from="Debtors - _TC",
			paid_to="_Test Cash - _TC",
		)
		pe.save()  # use save() to trigger set_liability_account()
		pe.submit()
		si = create_sales_invoice(company=COMPANY, qty=10, rate=100, customer="_Test Customer")

		pr = frappe.get_doc("Payment Reconciliation")
		pr.company = COMPANY
		pr.party_type = "Customer"
		pr.party = "_Test Customer"
		pr.receivable_payable_account = si.debit_to
		pr.default_advance_account = advance_account
		pr.payment_name = pe.name
		pr.invoice_name = si.name
		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		expected_ple = self.get_ple(pe.name)
		self.assertIn(si.name, [d.against_voucher_no for d in expected_ple])

		repost = self.submit_repost([pe])
		start_payment_ledger_repost(repost.name)

		self.assertEqual(self.get_repost_status(repost), "Completed")
		self.assertEqual(self.get_ple(pe.name), expected_ple)

	def test_repost_keeps_cost_center_allocation(self):
		for cost_center in ["RPL Main Cost Center", "RPL Sub Cost Center 1", "RPL Sub Cost Center 2"]:
			create_cost_center(cost_center_name=cost_center, company=COMPANY)
		create_cost_center_allocation(
			COMPANY,
			"RPL Main Cost Center - _TC",
			{"RPL Sub Cost Center 1 - _TC": 60, "RPL Sub Cost Center 2 - _TC": 40},
		)
		si = create_sales_invoice(
			company=COMPANY,
			rate=100,
			qty=1,
			cost_center="RPL Main Cost Center - _TC",
			parent_cost_center="RPL Main Cost Center - _TC",
		)

		expected_ple = self.get_ple(si.name)
		self.assertEqual(
			[(d.cost_center, d.amount) for d in expected_ple],
			[("RPL Sub Cost Center 1 - _TC", 60), ("RPL Sub Cost Center 2 - _TC", 40)],
		)

		repost = self.submit_repost([si])
		start_payment_ledger_repost(repost.name)

		self.assertEqual(self.get_repost_status(repost), "Completed")
		self.assertEqual(self.get_ple(si.name), expected_ple)
