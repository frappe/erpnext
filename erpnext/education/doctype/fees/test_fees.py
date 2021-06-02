# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate
from frappe.utils.make_random import get_random
from erpnext.education.doctype.program.test_program import make_program_and_linked_courses

test_dependencies = ['Company']
class TestFees(unittest.TestCase):

	def test_fees(self):
		student = get_random("Student")
		program = make_program_and_linked_courses("_Test Program 1", ["_Test Course 1", "_Test Course 2"])
		fee = frappe.new_doc("Fees")
		fee.posting_date = nowdate()
		fee.due_date = nowdate()
		fee.student = student
		fee.receivable_account = "_Test Receivable - _TC"
		fee.income_account = "Sales - _TC"
		fee.cost_center = "_Test Cost Center - _TC"
		fee.company = "_Test Company"
		fee.program = program.name

		fee.extend("components", [
			{
				"fees_category": "Tuition Fee",
				"amount": 40000
			},
			{
				"fees_category": "Transportation Fee",
				"amount": 10000
			}])
		fee.save()
		fee.submit()

		gl_entries = frappe.db.sql("""
			select account, posting_date, party_type, party, cost_center, fiscal_year, voucher_type,
			voucher_no, against_voucher_type, against_voucher, cost_center, company, credit, debit
			from `tabGL Entry` where voucher_type=%s and voucher_no=%s""", ("Fees", fee.name), as_dict=True)

		if gl_entries[0].account == "_Test Receivable - _TC":
			self.assertEqual(gl_entries[0].debit, 50000)
			self.assertEqual(gl_entries[0].credit, 0)
			self.assertEqual(gl_entries[1].debit, 0)
			self.assertEqual(gl_entries[1].credit, 50000)
		else:
			self.assertEqual(gl_entries[0].credit, 50000)
			self.assertEqual(gl_entries[0].debit, 0)
			self.assertEqual(gl_entries[1].credit, 0)
			self.assertEqual(gl_entries[1].debit, 50000)
