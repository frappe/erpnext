# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.hr.doctype.employee_advance.employee_advance import EmployeeAdvanceOverPayment

class TestEmployeeAdvance(unittest.TestCase):
	def test_paid_amount(self):
		advance = create_employee_advance()
		
		pe = create_payment_entry(advance)
		pe.submit()
		
		advance.reload()
		self.assertEqual(advance.paid_amount, 1000)
		
		return advance
				
		
def create_employee_advance():	
	advance = frappe.new_doc("Employee Advance")
	advance.employee = "_T-Employee-0001"
	advance.purpose = "Test"
	advance.advance_amount = 1000
	advance.approval_status = "Approved"
	advance.advance_account = "_Test Employee Advance - _TC"
	advance.company = "_Test Company"
	advance.save()
	advance.submit()
	return advance

def create_payment_entry(advance, amount=None):
	pe = frappe.get_doc(get_payment_entry(advance.doctype, advance.name))
	pe.reference_no = "123"
	pe.reference_date = nowdate()
	if amount:
		pe.paid_amount = amount
		pe.received_amount = amount
	pe.save()
	
	return pe