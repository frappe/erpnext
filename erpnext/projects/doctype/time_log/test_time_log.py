# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

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

test_records = frappe.get_test_records('Time Log')
test_ignore = ["Time Log Batch", "Sales Invoice"]
