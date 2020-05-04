# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile

class TestPOSInvoice(unittest.TestCase):
	pass

def create_pos_invoice(**args):
	args = frappe._dict(args)
	pos_profile = None
	if not args.pos_profile:
		pos_profile = make_pos_profile()
		pos_profile.save()

	pos_inv = frappe.new_doc("POS Invoice")
	pos_inv.update_stock = 1
	pos_inv.is_pos = 1
	pos_inv.pos_profile = args.pos_profile or pos_profile.name

	pos_inv.set_missing_values()

	if args.posting_date:
		pos_inv.set_posting_time = 1
	pos_inv.posting_date = args.posting_date or frappe.utils.nowdate()

	pos_inv.company = args.company or "_Test Company"
	pos_inv.customer = args.customer or "_Test Customer"
	pos_inv.debit_to = args.debit_to or "Debtors - _TC"
	pos_inv.is_return = args.is_return
	pos_inv.return_against = args.return_against
	pos_inv.currency=args.currency or "INR"
	pos_inv.conversion_rate = args.conversion_rate or 1

	pos_inv.append("items", {
		"item_code": args.item or args.item_code or "_Test Item",
		"gst_hsn_code": "999800",
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"qty": args.qty or 1,
		"rate": args.rate if args.get("rate") is not None else 100,
		"income_account": args.income_account or "Sales - _TC",
		"expense_account": args.expense_account or "Cost of Goods Sold - _TC",
		"cost_center": args.cost_center or "_Test Cost Center - _TC",
		"serial_no": args.serial_no
	})

	if not args.do_not_save:
		pos_inv.insert()
		if not args.do_not_submit:
			pos_inv.submit()
		else:
			pos_inv.payment_schedule = []
	else:
		pos_inv.payment_schedule = []

	return pos_inv