# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _
from webnotes.utils import cint

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		if cint(self.doc.extract_emails) and not (self.doc.email_id and self.doc.host and \
			self.doc.username and self.doc.password):
			
			webnotes.msgprint(_("""Host, Email and Password required if emails are to be pulled"""),
				raise_exception=True)