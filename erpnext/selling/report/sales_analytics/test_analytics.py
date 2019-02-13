# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
import unittest
from erpnext.selling.report.sales_analytics.sales_analytics import execute
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

class TestAnalytics(unittest.TestCase):
	def test_sales_analytics(self):
		self.maxDiff = None

		frappe.db.sql("delete from `tabSales Order` where company='_Test Company 2'")

		create_sales_orders()

		self.compare_result_for_customer()
		self.compare_result_for_customer_group()
		self.compare_result_for_customer_based_on_quantity()


	def compare_result_for_customer(self):
		filters = {
			'doctype': 'Sales Order',
			'range': 'Monthly',
			'from_date': '2017-04-01',
			'to_date': '2018-03-31',
			'tree_type': 'Customer',
			'company': '_Test Company 2',
			'value_field': 'base_net_amount'
		}

		report = execute(filters)

		expected_data = [
			{
				"entity": "'Total'",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 2000.0,
				"jul_2017": 1000.0,
				"aug_2017": 0.0,
				"sep_2017": 1500.0,
				"oct_2017": 1000.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 2000.0,
				"mar_2018": 0.0,
				"total": 7500.0
			},
			{
				"entity": "_Test Customer 1",
				"entity_name": "_Test Customer 1",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 0.0,
				"jul_2017": 0.0,
				"aug_2017": 0.0,
				"sep_2017": 0.0,
				"oct_2017": 0.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 2000.0,
				"mar_2018": 0.0,
				"total": 2000.0,
				"indent": 1
			},
			{
				"entity": "_Test Customer 2",
				"entity_name": "_Test Customer 2",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 0.0,
				"jul_2017": 0.0,
				"aug_2017": 0.0,
				"sep_2017": 1500.0,
				"oct_2017": 1000.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 0.0,
				"mar_2018": 0.0,
				"total": 2500.0,
				"indent": 1
			},
			{
				"entity": "_Test Customer 3",
				"entity_name": "_Test Customer 3",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 2000.0,
				"jul_2017": 1000.0,
				"aug_2017": 0.0,
				"sep_2017": 0.0,
				"oct_2017": 0.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 0.0,
				"mar_2018": 0.0,
				"total": 3000.0,
				"indent": 1
			}
		]
		result = sorted(report[1], key=lambda k: k['entity'])
		self.assertEqual(expected_data, result)

	def compare_result_for_customer_group(self):
		filters = {
			'doctype': 'Sales Order',
			'range': 'Monthly',
			'from_date': '2017-04-01',
			'to_date': '2018-03-31',
			'tree_type': 'Customer Group',
			'company': '_Test Company 2',
			'value_field': 'base_net_amount'
		}

		report = execute(filters)

		expected_first_row = {
			"entity": "All Customer Groups",
			"indent": 0,
			"apr_2017": 0.0,
			"may_2017": 0.0,
			"jun_2017": 2000.0,
			"jul_2017": 1000.0,
			"aug_2017": 0.0,
			"sep_2017": 1500.0,
			"oct_2017": 1000.0,
			"nov_2017": 0.0,
			"dec_2017": 0.0,
			"jan_2018": 0.0,
			"feb_2018": 2000.0,
			"mar_2018": 0.0,
			"total":7500.0
		}
		self.assertEqual(expected_first_row, report[1][0])

	def compare_result_for_customer_based_on_quantity(self):
		filters = {
			'doctype': 'Sales Order',
			'range': 'Monthly',
			'from_date': '2017-04-01',
			'to_date': '2018-03-31',
			'tree_type': 'Customer',
			'company': '_Test Company 2',
			'value_field': 'stock_qty'
		}

		report = execute(filters)

		expected_data = [
			{
				"entity": "'Total'",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 20.0,
				"jul_2017": 10.0,
				"aug_2017": 0.0,
				"sep_2017": 15.0,
				"oct_2017": 10.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 20.0,
				"mar_2018": 0.0,
				"total": 75.0
			},
			{
				"entity": "_Test Customer 1",
				"entity_name": "_Test Customer 1",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 0.0,
				"jul_2017": 0.0,
				"aug_2017": 0.0,
				"sep_2017": 0.0,
				"oct_2017": 0.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 20.0,
				"mar_2018": 0.0,
				"total": 20.0,
				"indent": 1
			},
			{
				"entity": "_Test Customer 2",
				"entity_name": "_Test Customer 2",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 0.0,
				"jul_2017": 0.0,
				"aug_2017": 0.0,
				"sep_2017": 15.0,
				"oct_2017": 10.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 0.0,
				"mar_2018": 0.0,
				"total": 25.0,
				"indent": 1
			},
			{
				"entity": "_Test Customer 3",
				"entity_name": "_Test Customer 3",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 20.0,
				"jul_2017": 10.0,
				"aug_2017": 0.0,
				"sep_2017": 0.0,
				"oct_2017": 0.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 0.0,
				"mar_2018": 0.0,
				"total": 30.0,
				"indent": 1
			}
		]
		result = sorted(report[1], key=lambda k: k['entity'])
		self.assertEqual(expected_data, result)

def create_sales_orders():
	frappe.set_user("Administrator")

	make_sales_order(company="_Test Company 2", qty=10,
		customer = "_Test Customer 1",
		transaction_date = '2018-02-10',
		warehouse = 'Finished Goods - _TC2',
		currency = 'EUR')

	make_sales_order(company="_Test Company 2",
		qty=10, customer = "_Test Customer 1",
		transaction_date = '2018-02-15',
		warehouse = 'Finished Goods - _TC2',
		currency = 'EUR')

	make_sales_order(company = "_Test Company 2",
		qty=10, customer = "_Test Customer 2",
		transaction_date = '2017-10-10',
		warehouse='Finished Goods - _TC2',
		currency = 'EUR')

	make_sales_order(company="_Test Company 2",
		qty=15, customer = "_Test Customer 2",
		transaction_date='2017-09-23',
		warehouse='Finished Goods - _TC2',
		currency = 'EUR')

	make_sales_order(company="_Test Company 2",
		qty=20, customer = "_Test Customer 3",
		transaction_date='2017-06-15',
		warehouse='Finished Goods - _TC2',
		currency = 'EUR')

	make_sales_order(company="_Test Company 2",
		qty=10, customer = "_Test Customer 3",
		transaction_date='2017-07-10',
		warehouse='Finished Goods - _TC2',
		currency = 'EUR')
