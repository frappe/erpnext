# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate, add_days
from erpnext.accounts.doctype.tax_rule.tax_rule import IncorrectCustomerGroup

# test_records = frappe.get_test_records('Tax Rule')

class TestTaxRule(unittest.TestCase):
	def test_customer_group(self):
		tax_rule = make_tax_rule_test_record(customer_group= "_Test Customer Group 1", do_not_save= True)
		self.assertRaises(IncorrectCustomerGroup, tax_rule.save)
		
	def test_tax_template(self):
		tax_rule = make_tax_rule_test_record()
		self.assertEquals(tax_rule.purchase_tax_template, None)

def make_tax_rule_test_record(**args):
	args = frappe._dict(args)
	
	tax_rule = frappe.new_doc("Tax Rule")
	tax_rule.customer= args.customer or "_Test Customer"
	tax_rule.customer_group= args.customer_group or "_Test Customer Group"
	tax_rule.billing_city= args.billing_city or "_Test City"
	tax_rule.billing_country= args.billing_country or "_Test Country"
	tax_rule.shipping_city= args.shipping_city or "_Test City"
	tax_rule.shipping_country= args.shipping_country or "_Test Country"
	tax_rule.from_date= args.from_date or nowdate()
	tax_rule.to_date= args.to_date or add_days(nowdate(), 1)
	tax_rule.tax_type= args.tax_type or "Sales"
	tax_rule.sales_tax_template= args.sales_tax_template or "_Test Sales Taxes and Charges Template"
	tax_rule.purchase_tax_template= args.purchase_tax_template or "_Test Purchase Taxes and Charges Template"
	tax_rule.priority= args.priority or 1
	tax_rule.compant= args.company or "_Test Company"
	
	if not args.do_not_save:
		tax_rule.save()
	return tax_rule
	