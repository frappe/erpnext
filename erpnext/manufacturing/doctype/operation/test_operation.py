# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

test_records = frappe.get_test_records('Operation')

class TestOperation(unittest.TestCase):
	pass

def make_operation(*args, **kwargs):
	args = args if args else kwargs
	if isinstance(args, tuple):
		args = args[0]

	args = frappe._dict(args)

	try:
		doc = frappe.get_doc({
			"doctype": "Operation",
			"name": args.operation,
			"workstation": args.workstation
		})

		doc.insert()

		return doc
	except frappe.DuplicateEntryError:
		return frappe.get_doc("Operation", args.operation)