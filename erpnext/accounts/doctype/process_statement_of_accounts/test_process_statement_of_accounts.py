# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts import (
	get_statement_dict,
	send_emails,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestProcessStatementOfAccounts(AccountsTestMixin, IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.enterClassContext(cls.change_settings("Selling Settings", validate_selling_price=0))

	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_customer(customer_name="Other Customer")
		self.clear_old_entries()
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

	def test_auto_email_for_process_soa_ar(self):
		process_soa = create_process_soa(
			name="_Test Process SOA", enable_auto_email=1, report="Accounts Receivable"
		)

		send_emails(process_soa.name, from_scheduler=True)
		process_soa.load_from_db()
		self.assertEqual(process_soa.posting_date, getdate(add_days(today(), 7)))

	def check_ageing_summary(self, ageing, expected_ageing):
		for age_range in expected_ageing:
			self.assertEqual(expected_ageing[age_range], ageing.get(age_range))

	def tearDown(self):
		frappe.db.rollback()


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
	process_soa.update(soa_dict)
	process_soa.save()
	return process_soa
