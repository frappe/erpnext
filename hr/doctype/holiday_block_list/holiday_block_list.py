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
