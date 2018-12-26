# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.support.doctype.service_level.test_service_level import make_service_level

class TestSupportContract(unittest.TestCase):
	
	def test_support_contract(self):
		test_make_support_contract = make_support_contract()
		test_get_support_contract = get_support_contract()
		self.assertEquals(test_make_support_contract, test_get_support_contract)

def make_support_contract():
	make_service_level()
	if not frappe.db.exists("Customer", "_Test Customer"):
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test Customer",
			"customer_group": "Commercial",
			"customer_type": "Individual",
			"territory": "Rest Of The World"
		}).insert()
	support_contract = frappe.get_doc({
		"doctype": "Support Contract",
		"customer": customer.customer_name,
		"service_level": "_Test Service Level",
		"holiday_list": "_Test Holiday List",
		"priority": "Medium",
		"employee_group": "_Test Employee Group",
		"start_date": frappe.utils.getdate(),
		"end_date": frappe.utils.add_to_date(frappe.utils.getdate(), days=100),
		"response_time": "5",
		"response_time_period": "Hour/s",
		"resolution_time": "2",
		"resolution_time_period": "Day/s",
	})
	support_contract_exists = frappe.db.exists("Support Contract", "Support Contract: _Test Customer")
	if not support_contract_exists:
		support_contract.insert()
		return support_contract.name
	else:
		return support_contract_exists

def get_support_contract():
	support_contract = frappe.db.exists("Support Contract", "Support Contract: _Test Customer")
	return support_contract