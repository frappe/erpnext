# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr, extract_email_id

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def autoname(self):
		# concat first and last name
		self.doc.name = " ".join(filter(None, 
			[cstr(self.doc.fields.get(f)).strip() for f in ["first_name", "last_name"]]))
		
		# concat party name if reqd
		for fieldname in ("customer", "supplier", "sales_partner"):
			if self.doc.fields.get(fieldname):
				self.doc.name = self.doc.name + "-" + cstr(self.doc.fields.get(fieldname)).strip()
				break
		
	def validate(self):
		self.set_status()
		self.validate_primary_contact()

	def validate_primary_contact(self):
		if self.doc.is_primary_contact == 1:
			if self.doc.customer:
				webnotes.conn.sql("update tabContact set is_primary_contact=0 where customer = '%s'" % (self.doc.customer))
			elif self.doc.supplier:
				webnotes.conn.sql("update tabContact set is_primary_contact=0 where supplier = '%s'" % (self.doc.supplier))	
			elif self.doc.sales_partner:
				webnotes.conn.sql("update tabContact set is_primary_contact=0 where sales_partner = '%s'" % (self.doc.sales_partner))
		else:
			if self.doc.customer:
				if not webnotes.conn.sql("select name from tabContact where is_primary_contact=1 and customer = '%s'" % (self.doc.customer)):
					self.doc.is_primary_contact = 1
			elif self.doc.supplier:
				if not webnotes.conn.sql("select name from tabContact where is_primary_contact=1 and supplier = '%s'" % (self.doc.supplier)):
					self.doc.is_primary_contact = 1
			elif self.doc.sales_partner:
				if not webnotes.conn.sql("select name from tabContact where is_primary_contact=1 and sales_partner = '%s'" % (self.doc.sales_partner)):
					self.doc.is_primary_contact = 1

	def on_trash(self):
		webnotes.conn.sql("""update `tabSupport Ticket` set contact='' where contact=%s""",
			self.doc.name)
