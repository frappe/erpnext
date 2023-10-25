import datetime

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, nowdate

from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.selling.report.payment_terms_status_for_sales_order.payment_terms_status_for_sales_order import (
	execute,
)
from erpnext.stock.doctype.item.test_item import create_item

test_dependencies = ["Sales Order", "Item", "Sales Invoice", "Payment Terms Template", "Customer"]


class TestPaymentTermsStatusForSalesOrder(FrappeTestCase):
	def setUp(self):
		self.cleanup_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def cleanup_old_entries(self):
		frappe.db.delete("Sales Invoice", filters={"company": "_Test Company"})
		frappe.db.delete("Sales Order", filters={"company": "_Test Company"})

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

	def test_01_payment_terms_status(self):
		self.create_payment_terms_template()
		item = create_item(item_code="_Test Excavator 1", is_stock_item=0)
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
			frappe._dict(
				{
					"company": "_Test Company",
					"period_start_date": "2021-06-01",
					"period_end_date": "2021-06-30",
					"item": item.item_code,
				}
			)
		)

		expected_value = [
			{
				"name": so.name,
				"customer": so.customer,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Completed",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 6, 30),
				"invoice_portion": 50.0,
				"currency": "INR",
				"base_payment_amount": 500000.0,
				"paid_amount": 500000.0,
				"invoices": "," + sinv.name,
			},
			{
				"name": so.name,
				"customer": so.customer,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Partly Paid",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 7, 15),
				"invoice_portion": 50.0,
				"currency": "INR",
				"base_payment_amount": 500000.0,
				"paid_amount": 100000.0,
				"invoices": "," + sinv.name,
			},
		]
		self.assertEqual(data, expected_value)

	def create_exchange_rate(self, date):
		# make an entry in Currency Exchange list. serves as a static exchange rate
		if frappe.db.exists(
			{"doctype": "Currency Exchange", "date": date, "from_currency": "USD", "to_currency": "INR"}
		):
			return
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Currency Exchange",
					"date": date,
					"from_currency": "USD",
					"to_currency": frappe.get_cached_value("Company", "_Test Company", "default_currency"),
					"exchange_rate": 70,
					"for_buying": True,
					"for_selling": True,
				}
			)
			doc.insert()

	def test_02_alternate_currency(self):
		transaction_date = "2021-06-15"
		self.create_payment_terms_template()
		self.create_exchange_rate(transaction_date)
		item = create_item(item_code="_Test Excavator 2", is_stock_item=0)
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
			frappe._dict(
				{
					"company": "_Test Company",
					"period_start_date": "2021-06-01",
					"period_end_date": "2021-06-30",
					"item": item.item_code,
				}
			)
		)

		# report defaults to company currency.
		expected_value = [
			{
				"name": so.name,
				"customer": so.customer,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Completed",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 6, 30),
				"invoice_portion": 50.0,
				"currency": frappe.get_cached_value("Company", "_Test Company", "default_currency"),
				"base_payment_amount": 3500000.0,
				"paid_amount": 3500000.0,
				"invoices": "," + sinv.name,
			},
			{
				"name": so.name,
				"customer": so.customer,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Partly Paid",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 7, 15),
				"invoice_portion": 50.0,
				"currency": frappe.get_cached_value("Company", "_Test Company", "default_currency"),
				"base_payment_amount": 3500000.0,
				"paid_amount": 700000.0,
				"invoices": "," + sinv.name,
			},
		]
		self.assertEqual(data, expected_value)

	def test_03_group_filters(self):
		transaction_date = "2021-06-15"
		self.create_payment_terms_template()
		item1 = create_item(item_code="_Test Excavator 1", is_stock_item=0)
		item1.item_group = "Products"
		item1.save()

		so1 = make_sales_order(
			transaction_date=transaction_date,
			delivery_date=add_days(transaction_date, -30),
			item=item1.item_code,
			qty=1,
			rate=1000000,
			do_not_save=True,
		)
		so1.po_no = ""
		so1.taxes_and_charges = ""
		so1.taxes = ""
		so1.payment_terms_template = self.template.name
		so1.save()
		so1.submit()

		item2 = create_item(item_code="_Test Steel", is_stock_item=0)
		item2.item_group = "Raw Material"
		item2.save()

		so2 = make_sales_order(
			customer="_Test Customer 1",
			transaction_date=transaction_date,
			delivery_date=add_days(transaction_date, -30),
			item=item2.item_code,
			qty=100,
			rate=1000,
			do_not_save=True,
		)
		so2.po_no = ""
		so2.taxes_and_charges = ""
		so2.taxes = ""
		so2.payment_terms_template = self.template.name
		so2.save()
		so2.submit()

		base_filters = {
			"company": "_Test Company",
			"period_start_date": "2021-06-01",
			"period_end_date": "2021-06-30",
		}

		expected_value_so1 = [
			{
				"name": so1.name,
				"customer": so1.customer,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Overdue",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 6, 30),
				"invoice_portion": 50.0,
				"currency": "INR",
				"base_payment_amount": 500000.0,
				"paid_amount": 0.0,
				"invoices": "",
			},
			{
				"name": so1.name,
				"customer": so1.customer,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Overdue",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 7, 15),
				"invoice_portion": 50.0,
				"currency": "INR",
				"base_payment_amount": 500000.0,
				"paid_amount": 0.0,
				"invoices": "",
			},
		]

		expected_value_so2 = [
			{
				"name": so2.name,
				"customer": so2.customer,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Overdue",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 6, 30),
				"invoice_portion": 50.0,
				"currency": "INR",
				"base_payment_amount": 50000.0,
				"paid_amount": 0.0,
				"invoices": "",
			},
			{
				"name": so2.name,
				"customer": so2.customer,
				"submitted": datetime.date(2021, 6, 15),
				"status": "Overdue",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date(2021, 7, 15),
				"invoice_portion": 50.0,
				"currency": "INR",
				"base_payment_amount": 50000.0,
				"paid_amount": 0.0,
				"invoices": "",
			},
		]

		group_filters = [
			{"customer_group": "All Customer Groups"},
			{"item_group": "All Item Groups"},
			{"item_group": "Products"},
			{"item_group": "Raw Material"},
		]

		expected_values_for_group_filters = [
			expected_value_so1 + expected_value_so2,
			expected_value_so1 + expected_value_so2,
			expected_value_so1,
			expected_value_so2,
		]

		for idx, g in enumerate(group_filters, 0):
			# build filter
			filters = frappe._dict({}).update(base_filters).update(g)
			with self.subTest(filters=filters):
				columns, data, message, chart = execute(filters)
				self.assertEqual(data, expected_values_for_group_filters[idx])

	def test_04_due_date_filter(self):
		self.create_payment_terms_template()
		item = create_item(item_code="_Test Excavator 1", is_stock_item=0)
		transaction_date = nowdate()
		so = make_sales_order(
			transaction_date=add_months(transaction_date, -1),
			delivery_date=add_days(transaction_date, -15),
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

		first_due_date = add_days(add_months(transaction_date, -1), 15)
		columns, data, message, chart = execute(
			frappe._dict(
				{
					"company": "_Test Company",
					"item": item.item_code,
					"from_due_date": add_months(transaction_date, -1),
					"to_due_date": first_due_date,
				}
			)
		)

		expected_value = [
			{
				"name": so.name,
				"customer": so.customer,
				"submitted": datetime.date.fromisoformat(add_months(transaction_date, -1)),
				"status": "Completed",
				"payment_term": None,
				"description": "_Test 50-50",
				"due_date": datetime.date.fromisoformat(first_due_date),
				"invoice_portion": 50.0,
				"currency": "INR",
				"base_payment_amount": 500000.0,
				"paid_amount": 500000.0,
				"invoices": "," + sinv.name,
			},
		]
		# Only the first term should be pulled
		self.assertEqual(len(data), 1)
		self.assertEqual(data, expected_value)
