# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts import (
	send_emails,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice


class TestProcessStatementOfAccounts(unittest.TestCase):
	def setUp(self):
		self.si = create_sales_invoice()
		self.process_soa = create_process_soa()

	def test_auto_email_for_process_soa_ar(self):
		send_emails(self.process_soa.name, from_scheduler=True)
		self.process_soa.load_from_db()
		self.assertEqual(self.process_soa.posting_date, getdate(add_days(today(), 7)))

	def tearDown(self):
		frappe.delete_doc_if_exists("Process Statement Of Accounts", "Test Process SOA")


def create_process_soa():
	frappe.delete_doc_if_exists("Process Statement Of Accounts", "Test Process SOA")
	process_soa = frappe.new_doc("Process Statement Of Accounts")
	soa_dict = {
		"name": "Test Process SOA",
		"company": "_Test Company",
	}
	process_soa.update(soa_dict)
	process_soa.set("customers", [{"customer": "_Test Customer"}])
	process_soa.enable_auto_email = 1
	process_soa.frequency = "Weekly"
	process_soa.report = "Accounts Receivable"
	process_soa.save()
	return process_soa
