# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.stock.get_item_details import get_pos_profile
from erpnext.accounts.doctype.sales_invoice.pos import get_items_list, get_customers_list

class TestPOSProfile(unittest.TestCase):
	def test_pos_profile(self):
		make_pos_profile()

		pos_profile = get_pos_profile("_Test Company") or {}
		if pos_profile:
			doc = frappe.get_doc("POS Profile", pos_profile.get("name"))
			doc.set('item_groups', [{'item_group': '_Test Item Group'}])
			doc.set('customer_groups', [{'customer_group': '_Test Customer Group'}])
			doc.save()
			items = get_items_list(doc, doc.company)
			customers = get_customers_list(doc)
			
			products_count = frappe.db.sql(""" select count(name) from tabItem where item_group = '_Test Item Group'""", as_list=1)
			customers_count = frappe.db.sql(""" select count(name) from tabCustomer where customer_group = '_Test Customer Group'""")

			self.assertEqual(len(items), products_count[0][0])
			self.assertEqual(len(customers), customers_count[0][0])

		frappe.db.sql("delete from `tabPOS Profile`")

def make_pos_profile(**args):
	frappe.db.sql("delete from `tabPOS Profile`")

	args = frappe._dict(args)

	pos_profile = frappe.get_doc({
		"company": args.company or "_Test Company",
		"cost_center": args.cost_center or "_Test Cost Center - _TC",
		"currency": args.currency or "INR",
		"doctype": "POS Profile",
		"expense_account": args.expense_account or "_Test Account Cost for Goods Sold - _TC",
		"income_account":  args.income_account or "Sales - _TC",
		"name":  args.name or "_Test POS Profile",
		"naming_series": "_T-POS Profile-",
		"selling_price_list":  args.selling_price_list or "_Test Price List",
		"territory": args.territory or  "_Test Territory",
		"customer_group": frappe.db.get_value('Customer Group', {'is_group': 0}, 'name'),
		"warehouse":  args.warehouse or "_Test Warehouse - _TC",
		"write_off_account":  args.write_off_account or "_Test Write Off - _TC",
		"write_off_cost_center":  args.write_off_cost_center or "_Test Write Off Cost Center - _TC"
	})

	if not frappe.db.exists("POS Profile", args.name or "_Test POS Profile"):
		pos_profile.insert()

	return pos_profile
