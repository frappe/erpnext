# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
import unittest

test_records = frappe.get_test_records('Salary Structure')

class TestSalaryStructure(unittest.TestCase):
	pass
