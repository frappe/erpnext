# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import today, add_days, getdate
from erpnext.accounts.utils import get_fiscal_year
from erpnext.accounts.report.financial_statements import get_months
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.subscription.doctype.subscription.subscription import make_subscription_entry

class TestSubscription(unittest.TestCase):
	def test_daily_subscription(self):
		if not frappe.db.get_value('Quotation', {'docstatus': 1}, 'name'):
			quotation = frappe.copy_doc(quotation_records[0])
			quotation.submit()

		doc = make_subscription()
		self.assertEquals(doc.next_schedule_date, today())

	def test_monthly_subscription(self):
		current_fiscal_year = get_fiscal_year(today(), as_dict=True)
		start_date = current_fiscal_year.year_start_date
		end_date = current_fiscal_year.year_end_date

		docname = create_sales_invoice(posting_date=start_date)
		doc = make_subscription(base_doctype='Sales Invoice', frequency = 'Monthly',
			base_docname = docname.name, start_date=start_date, end_date=end_date)

		doc.disabled = 1
		doc.save()

		make_subscription_entry()
		docnames = frappe.get_all(doc.base_doctype, {'subscription': doc.name})
		self.assertEquals(len(docnames), 1)

		doc.disabled = 0
		doc.save()

		months = get_months(getdate(start_date), getdate(today()))
		make_subscription_entry()
		docnames = frappe.get_all(doc.base_doctype, {'subscription': doc.name})
		self.assertEquals(len(docnames), months)

quotation_records = frappe.get_test_records('Quotation')

def make_subscription(**args):
	args = frappe._dict(args)
	doc = frappe.get_doc({
		'doctype': 'Subscription',
		'base_doctype': args.base_doctype or 'Quotation',
		'base_docname': args.base_docname or \
			frappe.db.get_value('Quotation', {'docstatus': 1}, 'name'),
		'frequency': args.frequency or 'Daily',
		'start_date': args.start_date or add_days(today(), -1),
		'end_date': args.end_date or add_days(today(), 1),
		'submit_on_creation': args.submit_on_creation or 0
	}).insert(ignore_permissions=True)

	if not args.do_not_submit:
		doc.submit()

	return doc