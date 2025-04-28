# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
<<<<<<< HEAD
import unittest

import frappe
from frappe.tests import IntegrationTestCase


class TestIssuePriority(IntegrationTestCase):
=======

import unittest

import frappe


class TestIssuePriority(unittest.TestCase):
>>>>>>> 7c4cf3e834 (Favicon.svg)
	def test_priorities(self):
		make_priorities()
		priorities = frappe.get_list("Issue Priority")

		for priority in priorities:
			self.assertIn(priority.name, ["Low", "Medium", "High"])


def make_priorities():
	insert_priority("Low")
	insert_priority("Medium")
	insert_priority("High")


def insert_priority(name):
	if not frappe.db.exists("Issue Priority", name):
		frappe.get_doc({"doctype": "Issue Priority", "name": name}).insert(ignore_permissions=True)
