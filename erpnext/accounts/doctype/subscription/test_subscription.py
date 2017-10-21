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
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.accounts.doctype.subscription.subscription import make_subscription_entry

class TestSubscription(unittest.TestCase):
	def test_daily_subscription(self):
		qo = frappe.copy_doc(quotation_records[0])
		qo.submit()

		doc = make_subscription(reference_document=qo.name)
		self.assertEquals(doc.next_schedule_date, today())
		make_subscription_entry()
		frappe.db.commit()

		quotation = frappe.get_doc(doc.reference_doctype, doc.reference_document)
		self.assertEquals(quotation.subscription, doc.name)

		new_quotation = frappe.db.get_value('Quotation',
			{'subscription': doc.name, 'name': ('!=', quotation.name)}, 'name')

		new_quotation = frappe.get_doc('Quotation', new_quotation)

		for fieldname in ['customer', 'company', 'order_type', 'total', 'net_total']:
			self.assertEquals(quotation.get(fieldname), new_quotation.get(fieldname))

		for fieldname in ['item_code', 'qty', 'rate', 'amount']:
			self.assertEquals(quotation.items[0].get(fieldname),
				new_quotation.items[0].get(fieldname))

	def test_monthly_subscription_for_so(self):
		current_fiscal_year = get_fiscal_year(today(), as_dict=True)
		start_date = current_fiscal_year.year_start_date
		end_date = current_fiscal_year.year_end_date

		for doctype in ['Sales Order', 'Sales Invoice']:
			if doctype == 'Sales Invoice':
				docname = create_sales_invoice(posting_date=start_date)
			else:
				docname = make_sales_order()

			self.monthly_subscription(doctype, docname.name, start_date, end_date)

	def monthly_subscription(self, doctype, docname, start_date, end_date):
		doc = make_subscription(reference_doctype=doctype, frequency = 'Monthly',
			reference_document = docname, start_date=start_date, end_date=end_date)

		doc.disabled = 1
		doc.save()
		frappe.db.commit()

		make_subscription_entry()
		docnames = frappe.get_all(doc.reference_doctype, {'subscription': doc.name})
		self.assertEquals(len(docnames), 1)

		doc = frappe.get_doc('Subscription', doc.name)
		doc.disabled = 0
		doc.save()

		months = get_months(getdate(start_date), getdate(today()))
		make_subscription_entry()

		docnames = frappe.get_all(doc.reference_doctype, {'subscription': doc.name})
		self.assertEquals(len(docnames), months)

quotation_records = frappe.get_test_records('Quotation')

def make_subscription(**args):
	args = frappe._dict(args)
	doc = frappe.get_doc({
		'doctype': 'Subscription',
		'reference_doctype': args.reference_doctype or 'Quotation',
		'reference_document': args.reference_document or \
			frappe.db.get_value('Quotation', {'docstatus': 1}, 'name'),
		'frequency': args.frequency or 'Daily',
		'start_date': args.start_date or add_days(today(), -1),
		'end_date': args.end_date or add_days(today(), 1),
		'submit_on_creation': args.submit_on_creation or 0
	}).insert(ignore_permissions=True)

	if not args.do_not_submit:
		doc.submit()

	return doc