# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
import unittest

from erpnext.projects.doctype.time_log.time_log import OverlapError
from erpnext.projects.doctype.time_log_batch.test_time_log_batch import *

class TestTimeLog(unittest.TestCase):
	def test_duplication(self):
		frappe.db.sql("delete from `tabTime Log`")
		frappe.get_doc(frappe.copy_doc(test_records[0])).insert()

		ts = frappe.get_doc(frappe.copy_doc(test_records[0]))
		self.assertRaises(OverlapError, ts.insert)

		frappe.db.sql("delete from `tabTime Log`")
	
	def test_negative_hours(self):
		frappe.db.sql("delete from `tabTime Log`")
		test_time_log = frappe.new_doc("Time Log")
		test_time_log.activity_type = "Communication"
		test_time_log.from_time = "2013-01-01 11:00:00.000000"
		test_time_log.to_time = "2013-01-01 10:00:00.000000"
		self.assertRaises(frappe.ValidationError, test_time_log.save)
		frappe.db.sql("delete from `tabTime Log`")

test_records = frappe.get_test_records('Time Log')
test_ignore = ["Time Log Batch", "Sales Invoice"]
