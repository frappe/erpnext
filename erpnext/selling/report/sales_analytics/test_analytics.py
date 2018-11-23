# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import frappe.defaults
import unittest
from erpnext.selling.report.sales_analytics.sales_analytics import execute
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

class TestAnalytics(unittest.TestCase):

	def test_by_entity(self):
		create_sales_order()

		filters = {
			'doc_type': 'Sales Order',
			'range': 'Monthly',
			'to_date': '2018-03-31',
			'tree_type': 'Customer',
			'company': '_Test Company 2',
			'from_date': '2017-04-01',
			'value_quantity': 'Value'
		}

		report = execute(filters)

		expected_data = [
			{
				"entity": "_Test Customer 1",
				"entity_name": "_Test Customer 1",
				"apr": 0.0,
				"may": 0.0,
				"jun": 0.0,
				"jul": 0.0,
				"aug": 0.0,
				"sep": 0.0,
				"oct": 0.0,
				"nov": 0.0,
				"dec": 0.0,
				"jan": 0.0,
				"feb": 2000.0,
				"mar": 0.0,
				"total":2000.0
			},
			{
				"entity": "_Test Customer 3",
				"entity_name": "_Test Customer 3",
				"apr": 0.0,
				"may": 0.0,
				"jun": 2000.0,
				"jul": 1000.0,
				"aug": 0.0,
				"sep": 0.0,
				"oct": 0.0,
				"nov": 0.0,
				"dec": 0.0,
				"jan": 0.0,
				"feb": 0.0,
				"mar": 0.0,
				"total": 3000.0
			},
			{
				"entity": "_Test Customer 2",
				"entity_name": "_Test Customer 2",
				"apr": 0.0,
				"may": 0.0,
				"jun": 0.0,
				"jul": 0.0,
				"aug": 0.0,
				"sep": 1500.0,
				"oct": 1000.0,
				"nov": 0.0,
				"dec": 0.0,
				"jan": 0.0,
				"feb": 0.0,
				"mar": 0.0,
				"total":2500.0
			}
		]
		self.assertEqual(expected_data, report[1])

	def test_by_group(self):
	
		filters = {
			'doc_type': 'Sales Order',
			'range': 'Monthly',
			'to_date': '2018-03-31',
			'tree_type': 'Customer Group',
			'company': '_Test Company 2',
			'from_date': '2017-04-01',
			'value_quantity': 'Value'
		}

		report = execute(filters)

		expected_data = [
			{
				"entity": "All Customer Groups",
				"indent": 0,
				"apr": 0.0,
				"may": 0.0,
				"jun": 2000.0,
				"jul": 1000.0,
				"aug": 0.0,
				"sep": 1500.0,
				"oct": 1000.0,
				"nov": 0.0,
				"dec": 0.0,
				"jan": 0.0,
				"feb": 2000.0,
				"mar": 0.0,
				"total":7500.0
			},
			{
				"entity": "Individual",
				"indent": 1,
				"apr": 0.0,
				"may": 0.0,
				"jun": 0.0,
				"jul": 0.0,
				"aug": 0.0,
				"sep": 0.0,
				"oct": 0.0,
				"nov": 0.0,
				"dec": 0.0,
				"jan": 0.0,
				"feb": 0.0,
				"mar": 0.0,
				"total": 0.0
			},
			{
				"entity": "_Test Customer Group",
				"indent": 1,
				"apr": 0.0,
				"may": 0.0,
				"jun": 0.0,
				"jul": 0.0,
				"aug": 0.0,
				"sep": 0.0,
				"oct": 0.0,
				"nov": 0.0,
				"dec": 0.0,
				"jan": 0.0,
				"feb": 0.0,
				"mar": 0.0,
				"total":0.0
			},
			{
				"entity": "_Test Customer Group 1",
				"indent": 1,
				"apr": 0.0,
				"may": 0.0,
				"jun": 0.0,
				"jul": 0.0,
				"aug": 0.0,
				"sep": 0.0,
				"oct": 0.0,
				"nov": 0.0,
				"dec": 0.0,
				"jan": 0.0,
				"feb": 0.0,
				"mar": 0.0,
				"total":0.0
			}
		]
		self.assertEqual(expected_data, report[1])
	
	def test_by_quantity(self):

		filters = {
			'doc_type': 'Sales Order',
			'range': 'Monthly',
			'to_date': '2018-03-31',
			'tree_type': 'Customer',
			'company': '_Test Company 2',
			'from_date': '2017-04-01',
			'value_quantity': 'Quantity'
		}

		report = execute(filters)

		expected_data = [
			{
				"entity": "_Test Customer 1",
				"entity_name": "_Test Customer 1",
				"apr": 0.0,
				"may": 0.0,
				"jun": 0.0,
				"jul": 0.0,
				"aug": 0.0,
				"sep": 0.0,
				"oct": 0.0,
				"nov": 0.0,
				"dec": 0.0,
				"jan": 0.0,
				"feb": 20.0,
				"mar": 0.0,
				"total":20.0
			},
			{
				"entity": "_Test Customer 3",
				"entity_name": "_Test Customer 3",
				"apr": 0.0,
				"may": 0.0,
				"jun": 20.0,
				"jul": 10.0,
				"aug": 0.0,
				"sep": 0.0,
				"oct": 0.0,
				"nov": 0.0,
				"dec": 0.0,
				"jan": 0.0,
				"feb": 0.0,
				"mar": 0.0,
				"total": 30.0
			},
			{
				"entity": "_Test Customer 2",
				"entity_name": "_Test Customer 2",
				"apr": 0.0,
				"may": 0.0,
				"jun": 0.0,
				"jul": 0.0,
				"aug": 0.0,
				"sep": 15.0,
				"oct": 10.0,
				"nov": 0.0,
				"dec": 0.0,
				"jan": 0.0,
				"feb": 0.0,
				"mar": 0.0,
				"total":25.0
			}
		]
		self.assertEqual(expected_data, report[1])

def create_sales_order():
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
		
