# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

# test_records = frappe.get_test_records('Newletter List')

class TestNewletterList(unittest.TestCase):
	def test_import(self):
		new_list = frappe.get_doc({
			"doctype": "Newsletter List",
			"title": "_Test Newsletter List 1"
		}).insert()

		n_leads = frappe.db.count("Lead")

		added = new_list.import_from("Lead")

		self.assertEquals(added, n_leads)

		frappe.delete_doc("Newsletter List", new_list.name)

test_dependencies = ["Lead"]

