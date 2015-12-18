# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

test_ignore = ["Account", "Cost Center"]

import frappe
import unittest

class TestOrganization(unittest.TestCase):
	pass


test_records = frappe.get_test_records('Organization')
