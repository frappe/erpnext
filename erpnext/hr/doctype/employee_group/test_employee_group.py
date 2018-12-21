# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.hr.doctype.employee.test_employee import make_employee

class TestEmployeeGroup(unittest.TestCase):
	make_employee("_Test Employee")

def make_employee_group():
#	frappe.get_doc({
#		"doctype": "Employee Group",
#		"employee_group_name": "_Test Employee Group",
#		"employee_list": [
#			{
#				
#			}
#		]
#	})
#	#if not frappe.db.get_value("User", user):#