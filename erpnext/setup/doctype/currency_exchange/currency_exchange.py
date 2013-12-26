# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint
from webnotes.model.controller import DocListController

class DocType(DocListController):
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def autoname(self):
		self.doc.name = self.doc.from_currency + "-" + self.doc.to_currency
		
	def validate(self):
		self.validate_value("exchange_rate", ">", 0)
		
		if self.doc.from_currency == self.doc.to_currency:
			msgprint(_("From Currency and To Currency cannot be same"), raise_exception=True)