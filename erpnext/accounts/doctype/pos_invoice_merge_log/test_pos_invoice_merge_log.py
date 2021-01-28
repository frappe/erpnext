# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice
from erpnext.accounts.doctype.pos_invoice.pos_invoice import make_sales_return
from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import consolidate_pos_invoices
from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import init_user_and_profile

class TestPOSInvoiceMergeLog(unittest.TestCase):
	def test_consolidated_invoice_creation(self):
		frappe.db.sql("delete from `tabPOS Invoice`")

		test_user, pos_profile = init_user_and_profile()

		pos_inv = create_pos_invoice(rate=300, do_not_submit=1)
		pos_inv.append('payments', {
			'mode_of_payment': 'Cash', 'account': 'Cash - _TC', 'amount': 300
		})
		pos_inv.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append('payments', {
			'mode_of_payment': 'Cash', 'account': 'Cash - _TC', 'amount': 3200
		})
		pos_inv2.submit()

		pos_inv3 = create_pos_invoice(customer="_Test Customer 2", rate=2300, do_not_submit=1)
		pos_inv3.append('payments', {
			'mode_of_payment': 'Cash', 'account': 'Cash - _TC', 'amount': 2300
		})
		pos_inv3.submit()

		consolidate_pos_invoices()

		pos_inv.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv.consolidated_invoice))

		pos_inv3.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv3.consolidated_invoice))

		self.assertFalse(pos_inv.consolidated_invoice == pos_inv3.consolidated_invoice)

		frappe.set_user("Administrator")
		frappe.db.sql("delete from `tabPOS Profile`")
		frappe.db.sql("delete from `tabPOS Invoice`")
	
	def test_consolidated_credit_note_creation(self):
		frappe.db.sql("delete from `tabPOS Invoice`")

		test_user, pos_profile = init_user_and_profile()

		pos_inv = create_pos_invoice(rate=300, do_not_submit=1)
		pos_inv.append('payments', {
			'mode_of_payment': 'Cash', 'account': 'Cash - _TC', 'amount': 300
		})
		pos_inv.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append('payments', {
			'mode_of_payment': 'Cash', 'account': 'Cash - _TC', 'amount': 3200
		})
		pos_inv2.submit()

		pos_inv3 = create_pos_invoice(customer="_Test Customer 2", rate=2300, do_not_submit=1)
		pos_inv3.append('payments', {
			'mode_of_payment': 'Cash', 'account': 'Cash - _TC', 'amount': 2300
		})
		pos_inv3.submit()

		pos_inv_cn = make_sales_return(pos_inv.name)
		pos_inv_cn.set("payments", [])
		pos_inv_cn.append('payments', {
			'mode_of_payment': 'Cash', 'account': 'Cash - _TC', 'amount': -300
		})
		pos_inv_cn.paid_amount = -300
		pos_inv_cn.submit()

		consolidate_pos_invoices()

		pos_inv.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv.consolidated_invoice))

		pos_inv3.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv3.consolidated_invoice))

		pos_inv_cn.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv_cn.consolidated_invoice))
		self.assertTrue(frappe.db.get_value("Sales Invoice", pos_inv_cn.consolidated_invoice, "is_return"))

		frappe.set_user("Administrator")
		frappe.db.sql("delete from `tabPOS Profile`")
		frappe.db.sql("delete from `tabPOS Invoice`")


