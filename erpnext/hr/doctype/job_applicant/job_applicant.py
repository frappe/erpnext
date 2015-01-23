# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import extract_email_id

class JobApplicant(Document):
	def validate(self):
		self.set_status()

	def set_sender(self, sender):
		"""Will be called by **Communication** when a Job Application is created from an incoming email."""
		self.email_id = sender
