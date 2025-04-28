# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
<<<<<<< HEAD
import unittest

import frappe
from frappe.tests import IntegrationTestCase


class TestProjectUpdate(IntegrationTestCase):
	pass
=======

import unittest

import frappe


class TestProjectUpdate(unittest.TestCase):
	pass


test_records = frappe.get_test_records("Project Update")
test_ignore = ["Sales Order"]
>>>>>>> 7c4cf3e834 (Favicon.svg)
