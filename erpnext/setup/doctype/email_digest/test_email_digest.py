# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.utils import add_days, today

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.tests.utils import ERPNextTestSuite


class TestEmailDigest(ERPNextTestSuite):
	def test_purchase_orders_items_overdue_list_is_filtered_by_company(self):
		digest = create_email_digest(
			company="_Test Company",
			frequency="Daily",
			purchase_orders_items_overdue=1,
			name="Test Email Digest PO Company Filter",
		)
		backdate = add_days(today(), -1)

		po1 = create_purchase_order(transaction_date=backdate, do_not_save=True)
		po1.schedule_date = backdate
		po1.items[0].schedule_date = backdate
		po1.insert()
		po1.submit()

		po2 = create_purchase_order(
			company="_Test Company 1",
			warehouse="Stores - _TC1",
			transaction_date=backdate,
			do_not_save=True,
		)
		po2.schedule_date = backdate
		po2.items[0].schedule_date = backdate
		po2.insert()
		po2.submit()

		overdue_items = digest.get_purchase_orders_items_overdue_list()

		self.assertIn(po1.name, overdue_items)
		self.assertNotIn(po2.name, overdue_items)


def create_email_digest(**args):
	args = frappe._dict(args)
	doc = frappe.new_doc("Email Digest")
	doc.name = args.name or "Test Email Digest"
	doc.company = args.company or "_Test Company"
	doc.frequency = args.frequency or "Daily"
	doc.enabled = args.enabled or 0
	doc.bank_balance = args.bank_balance or 0
	doc.credit_balance = args.credit_balance or 0
	doc.invoiced_amount = args.invoiced_amount or 0
	doc.payables = args.payables or 0
	doc.sales_orders_to_bill = args.sales_orders_to_bill or 0
	doc.purchase_orders_to_bill = args.purchase_orders_to_bill or 0
	doc.sales_order = args.sales_order or 0
	doc.purchase_order = args.purchase_order or 0
	doc.sales_orders_to_deliver = args.sales_orders_to_deliver or 0
	doc.purchase_orders_to_receive = args.purchase_orders_to_receive or 0
	doc.sales_invoice = args.sales_invoice or 0
	doc.purchase_invoice = args.purchase_invoice or 0
	doc.new_quotations = args.new_quotations or 0
	doc.pending_quotations = args.pending_quotations or 0
	doc.issue = args.issue or 0
	doc.project = args.project or 0
	doc.purchase_orders_items_overdue = args.purchase_orders_items_overdue or 0
	doc.calendar_events = args.calendar_events or 0
	doc.todo_list = args.todo_list or 0
	doc.notifications = args.notifications or 0
	doc.add_quote = args.add_quote or 0

	for recipient in args.recipients or ["Administrator"]:
		doc.append("recipients", {"recipient": recipient})

	if not args.do_not_save:
		doc.insert()

	return doc
