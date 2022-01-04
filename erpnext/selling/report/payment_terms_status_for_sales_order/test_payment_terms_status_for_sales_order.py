import datetime
import unittest

import frappe
from frappe import qb
from frappe.utils import add_days

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.selling.report.payment_terms_status_for_sales_order.payment_terms_status_for_sales_order import (
	execute,
)
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.tests.utils import ERPNextTestCase

test_dependencies = ["Sales Order", "Item", "Sales Invoice", "Payment Terms Template"]


class TestPaymentTermsStatusForSalesOrder(ERPNextTestCase):
	def test_payment_terms_status(self):
		# disable Must be a whole number
		nos = frappe.get_doc("UOM", "Nos")
		nos.must_be_whole_number = 0
		nos.save()

		template = None
		if frappe.db.exists("Payment Terms Template", "_Test 50-50"):
			template = frappe.get_doc("Payment Terms Template", "_Test 50-50")
		else:
			template = frappe.get_doc(
				{
					"doctype": "Payment Terms Template",
					"template_name": "_Test 50-50",
					"terms": [
						{
							"doctype": "Payment Terms Template Detail",
							"due_date_based_on": "Day(s) after invoice date",
							"payment_term_name": "_Test 50% on 15 Days",
							"description": "_Test 50-50",
							"invoice_portion": 50,
							"credit_days": 15,
						},
						{
							"doctype": "Payment Terms Template Detail",
							"due_date_based_on": "Day(s) after invoice date",
							"payment_term_name": "_Test 50% on 30 Days",
							"description": "_Test 50-50",
							"invoice_portion": 50,
							"credit_days": 30,
						},
					],
				}
			)
			template.insert()

		# item = create_item(item_code="_Test Excavator", is_stock_item=0, valuation_rate=1000000)
		item = create_item(item_code="_Test Excavator", is_stock_item=0)
		so = make_sales_order(
			transaction_date="2021-06-15",
			delivery_date=add_days("2021-06-15", -30),
			item=item.item_code,
			qty=1,
			rate=1000000,
			po_no=54321,
			do_not_save=True,
		)
		so.payment_terms_template = template.name
		so.save()
		so.submit()

		# make invoice with 60% of the total sales order value
		sinv = make_sales_invoice(so.name)
		# sinv.posting_date = "2021-06-29"
		sinv.items[0].qty *= 0.60
		sinv.insert()
		sinv.submit()

		columns, data, message, chart = execute(
			{
				"company": "_Test Company",
				"period_start_date": "2021-06-01",
				"period_end_date": "2021-06-30",
				"sales_order": [so.name],
			}
		)

		# revert changes to Nos
		nos.must_be_whole_number = 1
		nos.save()

		expected_value = [
			{
				"name": so.name,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Completed",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 6, 30),
				"invoice_portion": 50.0,
				"payment_amount": 500000.0,
				"paid_amount": 500000.0,
				"invoices": sinv.name,
			},
			{
				"name": so.name,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Partly Paid",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 7, 15),
				"invoice_portion": 50.0,
				"payment_amount": 500000.0,
				"paid_amount": 100000.0,
				"invoices": sinv.name,
			},
		]

		self.assertEqual(data, expected_value)
