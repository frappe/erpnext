import datetime

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days

from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.selling.report.payment_terms_status_for_sales_order.payment_terms_status_for_sales_order import (
	execute,
)
from erpnext.stock.doctype.item.test_item import create_item

test_dependencies = ["Sales Order", "Item", "Sales Invoice", "Payment Terms Template"]


class TestPaymentTermsStatusForSalesOrder(FrappeTestCase):
	def create_payment_terms_template(self):
		# create template for 50-50 payments
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
		self.template = template

	def test_payment_terms_status(self):
		self.create_payment_terms_template()
		item = create_item(item_code="_Test Excavator", is_stock_item=0)
		so = make_sales_order(
			transaction_date="2021-06-15",
			delivery_date=add_days("2021-06-15", -30),
			item=item.item_code,
			qty=10,
			rate=100000,
			do_not_save=True,
		)
		so.po_no = ""
		so.taxes_and_charges = ""
		so.taxes = ""
		so.payment_terms_template = self.template.name
		so.save()
		so.submit()

		# make invoice with 60% of the total sales order value
		sinv = make_sales_invoice(so.name)
		sinv.taxes_and_charges = ""
		sinv.taxes = ""
		sinv.items[0].qty = 6
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

		expected_value = [
			{
				"name": so.name,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Completed",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 6, 30),
				"invoice_portion": 50.0,
				"currency": "INR",
				"base_payment_amount": 500000.0,
				"paid_amount": 500000.0,
				"invoices": ","+sinv.name,
			},
			{
				"name": so.name,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Partly Paid",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 7, 15),
				"invoice_portion": 50.0,
				"currency": "INR",
				"base_payment_amount": 500000.0,
				"paid_amount": 100000.0,
				"invoices": ","+sinv.name,
			},
		]
		self.assertEqual(data, expected_value)

	def create_exchange_rate(self, date):
		# make an entry in Currency Exchange list. serves as a static exchange rate
		if frappe.db.exists({'doctype': "Currency Exchange",'date': date,'from_currency': 'USD', 'to_currency':'INR'}):
			return
		else:
			doc = frappe.get_doc({
				'doctype': "Currency Exchange",
				'date': date,
				'from_currency': 'USD',
				'to_currency': frappe.get_cached_value("Company", '_Test Company','default_currency'),
				'exchange_rate': 70,
				'for_buying': True,
				'for_selling': True
			})
			doc.insert()

	def test_alternate_currency(self):
		transaction_date = "2021-06-15"
		self.create_payment_terms_template()
		self.create_exchange_rate(transaction_date)
		item = create_item(item_code="_Test Excavator", is_stock_item=0)
		so = make_sales_order(
			transaction_date=transaction_date,
			currency="USD",
			delivery_date=add_days(transaction_date, -30),
			item=item.item_code,
			qty=10,
			rate=10000,
			do_not_save=True,
		)
		so.po_no = ""
		so.taxes_and_charges = ""
		so.taxes = ""
		so.payment_terms_template = self.template.name
		so.save()
		so.submit()

		# make invoice with 60% of the total sales order value
		sinv = make_sales_invoice(so.name)
		sinv.currency = "USD"
		sinv.taxes_and_charges = ""
		sinv.taxes = ""
		sinv.items[0].qty = 6
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

		# report defaults to company currency.
		expected_value = [
			{
				"name": so.name,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Completed",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 6, 30),
				"invoice_portion": 50.0,
				"currency": frappe.get_cached_value("Company", '_Test Company','default_currency'),
				"base_payment_amount": 3500000.0,
				"paid_amount": 3500000.0,
				"invoices": ","+sinv.name,
			},
			{
				"name": so.name,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Partly Paid",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 7, 15),
				"invoice_portion": 50.0,
				"currency": frappe.get_cached_value("Company", '_Test Company','default_currency'),
				"base_payment_amount": 3500000.0,
				"paid_amount": 700000.0,
				"invoices": ","+sinv.name,
			},
		]
		self.assertEqual(data, expected_value)
