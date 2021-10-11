# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

test_records = frappe.get_test_records('Warranty Claim')

class TestWarrantyClaim(unittest.TestCase):
	pass
