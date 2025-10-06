# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry


class TestFinanceBook(IntegrationTestCase):
	def test_finance_book(self):
		finance_book = create_finance_book()

		# create jv entry
		jv = make_journal_entry("_Test Bank - _TC", "Debtors - _TC", 100, save=False)

		jv.accounts[1].update({"party_type": "Customer", "party": "_Test Customer"})

		jv.finance_book = finance_book.finance_book_name
		jv.submit()

		# check the Finance Book in the GL Entry
		gl_entries = frappe.get_all(
			"GL Entry",
			fields=["name", "finance_book"],
			filters={"voucher_type": "Journal Entry", "voucher_no": jv.name},
		)

		for gl_entry in gl_entries:
			self.assertEqual(gl_entry.finance_book, finance_book.name)


def create_finance_book():
	if not frappe.db.exists("Finance Book", "_Test Finance Book"):
		finance_book = frappe.get_doc(
			{"doctype": "Finance Book", "finance_book_name": "_Test Finance Book"}
		).insert()
	else:
		finance_book = frappe.get_doc("Finance Book", "_Test Finance Book")

	return finance_book
