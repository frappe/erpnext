# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
import unittest

import frappe
from frappe.tests import IntegrationTestCase

test_records = frappe.get_test_records("Monthly Distribution")


class TestMonthlyDistribution(IntegrationTestCase):
	pass
