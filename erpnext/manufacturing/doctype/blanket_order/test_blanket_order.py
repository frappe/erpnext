# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import add_months, today
from erpnext import get_company_currency
from .blanket_order import make_sales_order, make_purchase_order

class TestBlanketOrder(unittest.TestCase):
	def test_sales_order_creation(self):
		bo = make_blanket_order(blanket_order_type="Selling")

		so = make_sales_order(bo.name)
		so.currency = get_company_currency(so.company)
		so.delivery_date = today()
		so.items[0].qty = 10
		so.submit()

		self.assertEqual(so.doctype, "Sales Order")
		self.assertEqual(len(so.get("items")), len(bo.get("items")))

		# check the rate, quantity and updation for the ordered quantity
		self.assertEqual(so.items[0].rate, bo.items[0].rate)

		bo = frappe.get_doc("Blanket Order", bo.name)
		self.assertEqual(so.items[0].qty, bo.items[0].ordered_qty)

		# test the quantity
		so1 = make_sales_order(bo.name)
		so1.currency = get_company_currency(so1.company)
		self.assertEqual(so1.items[0].qty, (bo.items[0].qty-bo.items[0].ordered_qty))


	def test_purchase_order_creation(self):
		bo = make_blanket_order(blanket_order_type="Purchasing")

		po = make_purchase_order(bo.name)
		po.currency = get_company_currency(po.company)
		po.schedule_date = today()
		po.items[0].qty = 10
		po.submit()

		self.assertEqual(po.doctype, "Purchase Order")
		self.assertEqual(len(po.get("items")), len(bo.get("items")))

		# check the rate, quantity and updation for the ordered quantity
		self.assertEqual(po.items[0].rate, po.items[0].rate)

		bo = frappe.get_doc("Blanket Order", bo.name)
		self.assertEqual(po.items[0].qty, bo.items[0].ordered_qty)

		# test the quantity
		po1 = make_sales_order(bo.name)
		po1.currency = get_company_currency(po1.company)
		self.assertEqual(po1.items[0].qty, (bo.items[0].qty-bo.items[0].ordered_qty))



def make_blanket_order(**args):
	args = frappe._dict(args)
	bo = frappe.new_doc("Blanket Order")
	bo.blanket_order_type = args.blanket_order_type
	bo.company = args.company or "_Test Company"

	if args.blanket_order_type == "Selling":
		bo.customer = args.customer or "_Test Customer"
	else:
		bo.supplier = args.supplier or "_Test Supplier"

	bo.from_date = today()
	bo.to_date = add_months(bo.from_date, months=12)

	bo.append("items", {
		"item_code": args.item_code or "_Test Item",
		"qty": args.quantity or 1000,
		"rate": args.rate or 100
	})
	
	bo.insert()
	bo.submit()
	return bo