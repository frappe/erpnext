# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.get_item_details import get_item_details
from frappe.test_runner import make_test_objects

def test_create_test_data():
	frappe.set_user("Administrator")
	# create test item
	if not frappe.db.exists("Item","_Test Tesla Car"):
		item = frappe.get_doc({
		"description": "_Test Tesla Car",
		"doctype": "Item",
		"has_batch_no": 0,
		"has_serial_no": 0,
		"inspection_required": 0,
		"is_stock_item": 1,
		"opening_stock":100,
		"is_sub_contracted_item": 0,
		"item_code": "_Test Tesla Car",
		"item_group": "_Test Item Group",
		"item_name": "_Test Tesla Car",
		"apply_warehouse_wise_reorder_level": 0,
		"warehouse":"_Test Warehouse - _TC",
		"gst_hsn_code": "999800",
		"valuation_rate": 5000,
		"standard_rate":5000,
		"item_defaults": [{
		"company": "_Test Company",
		"default_warehouse": "_Test Warehouse - _TC",
		"default_price_list":"_Test Price List",
		"expense_account": "_Test Account Cost for Goods Sold - _TC",
		"buying_cost_center": "_Test Cost Center - _TC",
		"selling_cost_center": "_Test Cost Center - _TC",
		"income_account": "Sales - _TC"
		}],
		"show_in_website": 1,
		"route":"-test-tesla-car",
		"website_warehouse": "_Test Warehouse - _TC"
		})
		item.insert()
	# create test item price
	item_price = frappe.get_list('Item Price', filters={'item_code': '_Test Tesla Car', 'price_list': '_Test Price List'}, fields=['name'])
	if len(item_price)==0:
		item_price = frappe.get_doc({
			"doctype": "Item Price",
			"item_code": "_Test Tesla Car",
			"price_list": "_Test Price List",
			"price_list_rate": 5000
		})
		item_price.insert()
	# create test item pricing rule
	if not frappe.db.exists("Pricing Rule","_Test Pricing Rule for _Test Item"):
		item_pricing_rule = frappe.get_doc({
		"doctype": "Pricing Rule",
		"title": "_Test Pricing Rule for _Test Item",
		"apply_on": "Item Code",
		"items": [{
			"item_code": "_Test Tesla Car"
		}],
		"warehouse":"_Test Warehouse - _TC",
		"coupon_code_based":1,
		"selling": 1,
		"rate_or_discount": "Discount Percentage",
		"discount_percentage": 30,
		"company": "_Test Company",
		"currency":"INR",
		"for_price_list":"_Test Price List"
		})
		item_pricing_rule.insert()
	# create test item sales partner
	if not frappe.db.exists("Sales Partner","_Test Coupon Partner"):
		sales_partner = frappe.get_doc({
		"doctype": "Sales Partner",
		"partner_name":"_Test Coupon Partner",
		"commission_rate":2,
		"referral_code": "COPART"
		})
		sales_partner.insert()
	# create test item coupon code
	if not frappe.db.exists("Coupon Code","SAVE30"):
		coupon_code = frappe.get_doc({
		"doctype": "Coupon Code",
		"coupon_name":"SAVE30",
		"coupon_code":"SAVE30",
		"pricing_rule": "_Test Pricing Rule for _Test Item",
		"valid_from": "2014-01-01",
		"maximum_use":1,
		"used":0
		})
		coupon_code.insert()


class TestCouponCode(unittest.TestCase):
	def setUp(self):
		test_create_test_data()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_1_check_coupon_code_used_before_so(self):
		coupon_code = frappe.get_doc("Coupon Code", frappe.db.get_value("Coupon Code", {"coupon_name":"SAVE30"}))
		# reset used coupon code count
		coupon_code.used=0
		coupon_code.save()
		# check no coupon code is used before sales order is made
		self.assertEqual(coupon_code.get("used"),0)

	def test_2_sales_order_with_coupon_code(self):
		so = make_sales_order(customer="_Test Customer",selling_price_list="_Test Price List",item_code="_Test Tesla Car", rate=5000,qty=1, do_not_submit=True)
		so = frappe.get_doc('Sales Order', so.name)
		# check item price before coupon code is applied
		self.assertEqual(so.items[0].rate, 5000)
		so.coupon_code='SAVE30'
		so.sales_partner='_Test Coupon Partner'
		so.save()
		# check item price after coupon code is applied
		self.assertEqual(so.items[0].rate, 3500)	
		so.submit()

	def test_3_check_coupon_code_used_after_so(self):
		doc = frappe.get_doc("Coupon Code", frappe.db.get_value("Coupon Code", {"coupon_name":"SAVE30"}))
		# check no coupon code is used before sales order is made
		self.assertEqual(doc.get("used"),1)



