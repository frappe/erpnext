# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

test_records = frappe.get_test_records('Expense Claim')

class TestExpenseClaim(unittest.TestCase):
	pass
