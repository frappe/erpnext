# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts import (
	get_statement_dict,
	send_auto_email,
	send_emails,
	set_ageing,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestProcessStatementOfAccounts(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		frappe.db.set_single_value("Selling Settings", "validate_selling_price", 0)
		frappe.db.set_value(
			"Letter Head",
			"Company Letterhead - Grey",
			"is_default",
			0,
			update_modified=False,
		)

		self.company = "_Test Company"
		self.create_customer(customer_name="Other Customer")
		self.si = create_sales_invoice()
		create_sales_invoice(customer="Other Customer")

	def test_process_soa_for_gl(self):
		"""Tests the utils for Statement of Accounts(General Ledger)"""
		process_soa = create_process_soa(
			name="_Test Process SOA for GL",
			customers=[{"customer": "_Test Customer"}, {"customer": "Other Customer"}],
		)
		statement_dict = get_statement_dict(process_soa, get_statement_dict=True)

		# Checks if the statements are filtered based on the Customer
		self.assertIn("Other Customer", statement_dict)
		self.assertIn("_Test Customer", statement_dict)

		# Checks if the correct number of receivable entries exist
		# 3 rows for opening and closing and 1 row for SI
		receivable_entries = statement_dict["_Test Customer"][0]
		self.assertEqual(len(receivable_entries), 4)

		# Checks the amount for the receivable entry
		self.assertEqual(receivable_entries[1].voucher_no, self.si.name)
		self.assertEqual(receivable_entries[1].balance, 100)

	def test_process_soa_for_gl_normalizes_account_labels(self):
		"""GL opening/total/closing rows keep valid string account labels after normalization"""
		process_soa = create_process_soa(name="_Test Process SOA for GL Labels")
		statement_dict = get_statement_dict(process_soa, get_statement_dict=True)

		# normalization runs on the opening, total and closing rows of a customer with entries
		rows = statement_dict["_Test Customer"][0]
		for idx in (0, -2, -1):
			self.assertIsInstance(rows[idx]["account"], str)

	def test_process_soa_for_gl_with_no_transactions(self):
		"""GL statement for a period with no entries is skipped without error"""
		process_soa = create_process_soa(
			name="_Test Process SOA for GL No Data",
			from_date=add_days(today(), 365),
			to_date=add_days(today(), 395),
			posting_date=add_days(today(), 395),
		)
		statement_dict = get_statement_dict(process_soa, get_statement_dict=True)
		self.assertEqual(statement_dict, {})

	def test_process_soa_for_ar(self):
		"""Tests the utils for Statement of Accounts(Accounts Receivable)"""
		process_soa = create_process_soa(name="_Test Process SOA for AR", report="Accounts Receivable")
		statement_dict = get_statement_dict(process_soa, get_statement_dict=True)

		# Checks if the statements are filtered based on the Customer
		self.assertNotIn("Other Customer", statement_dict)
		self.assertIn("_Test Customer", statement_dict)

		# Checks if the correct number of receivable entries exist
		receivable_entries = statement_dict["_Test Customer"][0]
		self.assertEqual(len(receivable_entries), 1)

		# Checks the amount for the receivable entry
		self.assertEqual(receivable_entries[0].voucher_no, self.si.name)
		self.assertEqual(receivable_entries[0].total_due, 100)

		# Checks the ageing summary for AR
		ageing_summary = statement_dict["_Test Customer"][1][0]
		expected_summary = frappe._dict(
			range1=100,
			range2=0,
			range3=0,
			range4=0,
			range5=0,
		)
		self.check_ageing_summary(ageing_summary, expected_summary)

	@patch(
		"erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts.get_pdf",
		return_value=b"%PDF",
	)
	def test_auto_email_for_process_soa_ar(self, get_pdf):
		process_soa = create_process_soa(
			name="_Test Process SOA", enable_auto_email=1, report="Accounts Receivable"
		)

		send_emails(process_soa.name, from_scheduler=True)
		get_pdf.assert_called()
		process_soa.load_from_db()
		self.assertEqual(process_soa.posting_date, getdate(add_days(today(), 7)))

	def test_future_start_date_sets_receivable_posting_date(self):
		start_date = add_days(today(), 5)
		process_soa = create_process_soa(
			name="_Test Process SOA Start AR",
			enable_auto_email=1,
			report="Accounts Receivable",
			start_date=start_date,
		)
		self.assertEqual(getdate(process_soa.posting_date), getdate(start_date))

	def test_edit_keeps_the_next_send_date(self):
		start_date = add_days(today(), 5)
		process_soa = create_process_soa(
			name="_Test Process SOA Edit", enable_auto_email=1, start_date=start_date
		)
		# the scheduler moves the date after a send
		next_send = add_days(start_date, 7)
		process_soa.db_set("to_date", next_send)
		process_soa.reload()

		process_soa.subject = "Statement"
		process_soa.save()
		self.assertEqual(getdate(process_soa.to_date), getdate(next_send))

	@patch("erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts.send_emails")
	def test_auto_email_selects_due_and_missed_runs(self, send_emails):
		missed_gl = create_process_soa(name="_Test Process SOA Missed GL", enable_auto_email=1)
		missed_gl.db_set({"to_date": add_days(today(), -3), "posting_date": add_days(today(), 4)})
		missed_ar = create_process_soa(
			name="_Test Process SOA Missed AR", enable_auto_email=1, report="Accounts Receivable"
		)
		missed_ar.db_set({"posting_date": add_days(today(), -3), "to_date": add_days(today(), 4)})
		future_ar = create_process_soa(
			name="_Test Process SOA Future AR",
			enable_auto_email=1,
			report="Accounts Receivable",
			start_date=add_days(today(), 5),
		)

		send_auto_email()
		selected = {call.args[0] for call in send_emails.call_args_list}
		self.assertIn(missed_gl.name, selected)
		self.assertIn(missed_ar.name, selected)
		self.assertNotIn(future_ar.name, selected)

	def test_gl_ageing_is_as_of_to_date(self):
		to_date = add_days(today(), 45)
		process_soa = create_process_soa(name="_Test Process SOA GL Ageing", to_date=to_date)
		with patch(
			"erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts.get_ageing",
			return_value=([], []),
		) as get_ageing:
			set_ageing(process_soa, frappe._dict(customer="_Test Customer"))
		self.assertEqual(getdate(get_ageing.call_args.args[0].report_date), getdate(to_date))

	def check_ageing_summary(self, ageing, expected_ageing):
		for age_range in expected_ageing:
			self.assertEqual(expected_ageing[age_range], ageing.get(age_range))


def create_process_soa(**args):
	args = frappe._dict(args)
	frappe.delete_doc_if_exists("Process Statement Of Accounts", args.name)
	process_soa = frappe.new_doc("Process Statement Of Accounts")
	soa_dict = frappe._dict(
		name=args.name,
		company=args.company or "_Test Company",
		customers=args.customers or [{"customer": "_Test Customer"}],
		enable_auto_email=1 if args.enable_auto_email else 0,
		currency=args.currency or "",
		frequency=args.frequency or "Weekly",
		report=args.report or "General Ledger",
		from_date=args.from_date or getdate(today()),
		to_date=args.to_date or getdate(today()),
		posting_date=args.posting_date or getdate(today()),
		include_ageing=1,
	)
	if args.start_date:
		soa_dict.start_date = args.start_date
	process_soa.update(soa_dict)
	process_soa.save()
	return process_soa


class TestProcessStatementOfAccountsValidation(ERPNextTestSuite):
	"""validate() fills in default subject/body/pdf templates and enforces the
	basic constraints. Exercised on the document directly (no email/PDF flow)."""

	def make_soa(self, report="Accounts Receivable", with_customer=True, **overrides):
		doc = frappe.new_doc("Process Statement Of Accounts")
		doc.report = report
		doc.company = "_Test Company"
		if with_customer:
			doc.append("customers", {"customer": "_Test Customer"})
		doc.update(overrides)
		return doc

	def test_customers_are_required(self):
		self.assertRaises(frappe.ValidationError, self.make_soa(with_customer=False).validate)

	def test_general_ledger_body_uses_a_date_range(self):
		doc = self.make_soa(report="General Ledger")
		doc.validate()
		self.assertIn("from {{ doc.from_date }} to {{ doc.to_date }}", doc.body)
		# subject and pdf name are also defaulted
		self.assertTrue(doc.subject)
		self.assertTrue(doc.pdf_name)

	def test_receivable_body_uses_the_posting_date(self):
		doc = self.make_soa(report="Accounts Receivable")
		doc.validate()
		self.assertIn("until {{ doc.posting_date }}", doc.body)

	def test_account_must_belong_to_company(self):
		other = frappe.db.get_value("Account", {"company": "_Test Company 1", "is_group": 0}, "name")
		self.assertTrue(other, "need an account in _Test Company 1")
		self.assertRaises(frappe.ValidationError, self.make_soa(account=other).validate)
