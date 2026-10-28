# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.utils import add_days, add_months, getdate, today
from freezegun import freeze_time

from erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts import (
	get_statement_dict,
	send_auto_email,
	send_emails,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestProcessStatementOfAccounts(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		frappe.db.set_single_value("Selling Settings", "validate_selling_price", 0)
		letterhead = frappe.get_doc("Letter Head", "Company Letterhead - Grey")
		letterhead.is_default = 0
		letterhead.save()

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

	def test_ageing_uses_the_statement_report_date(self):
		with freeze_time("2026-12-02"):
			self.create_customer(customer_name="_Test Statement Ageing Customer")
			for posting_date, amount in (("2026-05-10", 1000), ("2026-09-25", 5000)):
				invoice = create_sales_invoice(
					customer=self.customer, posting_date=posting_date, rate=amount, do_not_save=True
				)
				invoice.due_date = posting_date
				invoice.insert().submit()

			for report, outstanding, range1, range5 in (
				("General Ledger", 6000, 5000, 1000),
				("Accounts Receivable", 1000, 0, 1000),
			):
				with self.subTest(report=report):
					process_soa = create_process_soa(
						name=f"_Test Ageing {report}",
						report=report,
						customers=[{"customer": self.customer}],
						from_date="2026-04-01",
						to_date="2026-10-02",
						posting_date="2026-06-01",
					)
					ageing = get_statement_dict(process_soa, get_statement_dict=True)[self.customer][1][0]
					self.assertEqual(ageing.outstanding, outstanding)
					self.check_ageing_summary(
						ageing, {"range1": range1, "range2": 0, "range3": 0, "range4": 0, "range5": range5}
					)

	@patch(
		"erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts.get_pdf",
		return_value=b"%PDF",
	)
	def test_auto_email_for_process_soa_ar(self, get_pdf):
		process_soa = create_process_soa(
			name="_Test Process SOA", enable_auto_email=1, report="Accounts Receivable"
		)

		send_emails(process_soa.name, from_scheduler=True)
		process_soa.load_from_db()
		self.assertEqual(process_soa.posting_date, getdate(add_days(today(), 7)))

	def test_auto_email_respects_start_date(self):
		with (
			freeze_time("2026-10-02"),
			patch(
				"erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts.get_report_pdf",
				return_value={"_Test Customer": b"%PDF"},
			) as get_report_pdf,
			patch("frappe.enqueue") as enqueue,
		):
			for report, date_field in (
				("General Ledger", "to_date"),
				("Accounts Receivable", "posting_date"),
			):
				for report_date, next_date in (
					("2026-10-22", "2026-11-22"),
					("2026-10-02", "2026-11-02"),
				):
					with self.subTest(report=report, report_date=report_date):
						process_soa = create_process_soa(
							name=f"_Test Scheduled {report} {report_date}",
							report=report,
							enable_auto_email=1,
							frequency="Monthly",
							start_date="2026-10-22",
							customers=[
								{"customer": "_Test Customer", "billing_email": "billing@example.com"}
							],
						)
						self.assertEqual(getdate(process_soa.get(date_field)), getdate("2026-10-22"))
						# Existing statements can retain a report date earlier than their start date.
						process_soa.set(date_field, report_date)
						process_soa.save()
						get_report_pdf.reset_mock()
						enqueue.reset_mock()
						send_auto_email()
						get_report_pdf.assert_not_called()
						enqueue.assert_not_called()

						with freeze_time("2026-10-22"):
							send_auto_email()
						get_report_pdf.assert_called_once()
						enqueue.assert_called_once()
						self.assertEqual(enqueue.call_args.kwargs["recipients"], ["billing@example.com"])
						self.assertEqual(process_soa.reload().get(date_field), getdate(next_date))

	def test_auto_email_recovers_missed_runs_and_preserves_schedule(self):
		with (
			patch(
				"erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts.get_report_pdf",
				return_value={"_Test Customer": b"%PDF"},
			),
			patch("frappe.enqueue") as enqueue,
		):
			for report, date_field in (
				("General Ledger", "to_date"),
				("Accounts Receivable", "posting_date"),
			):
				for frequency, start_date, next_date in (
					("Monthly", "2026-10-02", "2026-11-02"),
					("Daily", "2026-09-30", "2026-10-03"),
					("Weekly", "2026-09-18", "2026-10-09"),
					("Biweekly", "2026-09-04", "2026-10-16"),
					("Monthly", "2026-08-02", "2026-11-02"),
					("Quarterly", "2026-03-02", "2026-12-02"),
				):
					with self.subTest(report=report, frequency=frequency, start_date=start_date):
						with freeze_time(start_date):
							process_soa = create_process_soa(
								name=f"_Test Scheduled {report} {frequency} {start_date}",
								report=report,
								enable_auto_email=1,
								frequency=frequency,
								customers=[
									{"customer": "_Test Customer", "billing_email": "billing@example.com"}
								],
							)
						with freeze_time("2026-10-02"):
							enqueue.reset_mock()
							send_auto_email()
							enqueue.assert_called_once()
							self.assertEqual(process_soa.reload().get(date_field), getdate(next_date))

							process_soa.subject = "Updated statement subject"
							process_soa.save()
							self.assertEqual(process_soa.reload().get(date_field), getdate(next_date))
							enqueue.reset_mock()
							send_auto_email()
							enqueue.assert_not_called()

							process_soa.report = (
								"Accounts Receivable" if report == "General Ledger" else "General Ledger"
							)
							process_soa.save()
							process_soa.reload()
							if process_soa.report == "General Ledger":
								self.assertEqual(process_soa.to_date, getdate(next_date))
								self.assertEqual(process_soa.from_date, add_months(getdate(next_date), -1))
							else:
								self.assertEqual(process_soa.posting_date, getdate(next_date))
							send_auto_email()
							enqueue.assert_not_called()

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
		start_date=args.start_date or getdate(today()),
		report=args.report or "General Ledger",
		from_date=args.from_date or getdate(today()),
		to_date=args.to_date or getdate(today()),
		posting_date=args.posting_date or getdate(today()),
		include_ageing=1,
	)
	process_soa.update(soa_dict)
	process_soa.save()
	return process_soa
