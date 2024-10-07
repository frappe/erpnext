# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.tests import IntegrationTestCase


class TestProjectUpdate(IntegrationTestCase):
	pass


test_records = frappe.get_test_records("Project Update")
test_ignore = ["Sales Order"]
