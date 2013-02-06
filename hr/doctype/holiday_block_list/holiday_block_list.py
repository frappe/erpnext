# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from accounts.utils import validate_fiscal_year
from webnotes import _

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		dates = []
		for d in self.doclist.get({"doctype":"Holiday Block List Date"}):
			# validate fiscal year
			validate_fiscal_year(d.block_date, self.doc.year, _("Block Date"))
			
			# date is not repeated
			if d.block_date in dates:
				webnotes.msgprint(_("Date is repeated") + ":" + d.block_date, raise_exception=1)
			dates.append(d.block_date)

test_records = [[{
		"doctype":"Holiday Block List",
		"holiday_block_list_name": "_Test Holiday Block List",
		"year": "_Test Fiscal Year"
	}, {
		"doctype": "Holiday Block List Date",
		"parent": "_Test Holiday Block List",
		"parenttype": "Holiday Block List",
		"parentfield": "holiday_block_list_dates",
		"block_date": "2013-01-02",
		"reason": "First work day"
	}, {
		"doctype": "Holiday Block List Allow",
		"parent": "_Test Holiday Block List",
		"parenttype": "Holiday Block List",
		"parentfield": "holiday_block_list_allowed",
		"allow_user": "test1@erpnext.com",
		}
	]]