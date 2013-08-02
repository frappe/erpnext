# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _
from webnotes.utils import cint

class DocType:
	def __init__(self,doc,doclist=[]):
		self.doc, self.doclist = doc,doclist

	def get_series(self):
		import webnotes.model.doctype
		docfield = webnotes.model.doctype.get('Sales Invoice')
		series = [d.options for d in docfield 
			if d.doctype == 'DocField' and d.fieldname == 'naming_series']
		return series and series[0] or ''

	def validate(self):
		self.check_for_duplicate()
		self.validate_expense_account()
		
	def check_for_duplicate(self):
		res = webnotes.conn.sql("""select name, user from `tabPOS Setting` 
			where ifnull(user, '') = %s and name != %s and company = %s""", 
			(self.doc.user, self.doc.name, self.doc.company))
		if res:
			if res[0][1]:
				msgprint("POS Setting '%s' already created for user: '%s' and company: '%s'" % 
					(res[0][0], res[0][1], self.doc.company), raise_exception=1)
			else:
				msgprint("Global POS Setting already created - %s for this company: '%s'" % 
					(res[0][0], self.doc.company), raise_exception=1)

	def validate_expense_account(self):
		if cint(webnotes.defaults.get_global_default("auto_inventory_accounting")) \
				and not self.doc.expense_account:
			msgprint(_("Expense Account is mandatory"), raise_exception=1)