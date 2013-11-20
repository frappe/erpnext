# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
import unittest

from projects.doctype.time_log.time_log import OverlapError

class TestTimeLog(unittest.TestCase):
	def test_duplication(self):		
		ts = webnotes.bean(webnotes.copy_doclist(test_records[0]))
		self.assertRaises(OverlapError, ts.insert)

test_records = [[{
	"doctype": "Time Log",
	"from_time": "2013-01-01 10:00:00",
	"to_time": "2013-01-01 11:00:00",
	"activity_type": "_Test Activity Type",
	"note": "_Test Note",
	"docstatus": 1
}]]

test_ignore = ["Sales Invoice", "Time Log Batch"]