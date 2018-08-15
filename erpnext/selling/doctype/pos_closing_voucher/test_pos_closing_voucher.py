# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
import frappe
import unittest
from frappe.utils import nowdate
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile

class TestPOSClosingVoucher(unittest.TestCase):
	def test_pos_closing_voucher(self):
		old_user = frappe.session.user
		user = 'test@example.com'
		test_user = frappe.get_doc('User', user)

		roles = ("Accounts Manager", "Accounts User", "Sales Manager")
		test_user.add_roles(*roles)
		frappe.set_user(user)

		pos_profile = make_pos_profile()
		pos_profile.append('applicable_for_users', {
			'default': 1,
			'user': user
		})

		pos_profile.save()

		si1 = create_sales_invoice(is_pos=1, rate=3500, do_not_submit=1)
		si1.append('payments', {
			'mode_of_payment': 'Cash', 'account': 'Cash - _TC', 'amount': 3500
		})
		si1.submit()

		si2 = create_sales_invoice(is_pos=1, rate=3200, do_not_submit=1)
		si2.append('payments', {
			'mode_of_payment': 'Cash', 'account': 'Cash - _TC', 'amount': 3200
		})
		si2.submit()

		pcv_doc = create_pos_closing_voucher(user=user,
			pos_profile=pos_profile.name, collected_amount=6700)

		pcv_doc.get_closing_voucher_details()

		self.assertEqual(pcv_doc.total_quantity, 2)
		self.assertEqual(pcv_doc.net_total, 6700)

		payment = pcv_doc.payment_reconciliation[0]
		self.assertEqual(payment.mode_of_payment, 'Cash')

		si1.load_from_db()
		si1.cancel()

		si2.load_from_db()
		si2.cancel()

		test_user.load_from_db()
		test_user.remove_roles(*roles)

		frappe.set_user(old_user)
		frappe.db.sql("delete from `tabPOS Profile`")

def create_pos_closing_voucher(**args):
	args = frappe._dict(args)

	doc = frappe.get_doc({
		'doctype': 'POS Closing Voucher',
		'period_start_date': args.period_start_date or nowdate(),
		'period_end_date': args.period_end_date or nowdate(),
		'posting_date': args.posting_date or nowdate(),
		'company': args.company or "_Test Company",
		'pos_profile': args.pos_profile,
		'user': args.user or "Administrator",
	})

	doc.get_closing_voucher_details()
	if doc.get('payment_reconciliation'):
		doc.payment_reconciliation[0].collected_amount = (args.collected_amount or
			doc.payment_reconciliation[0].expected_amount)

	doc.save()
	return doc