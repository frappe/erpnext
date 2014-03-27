# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint

from frappe.model.document import Document

class SalesEmailSettings(Document):
		
	def validate(self):
		if cint(self.doc.extract_emails) and not (self.doc.email_id and self.doc.host and \
			self.doc.username and self.doc.password):
			
			frappe.msgprint(_("""Host, Email and Password required if emails are to be pulled"""),
				raise_exception=True)