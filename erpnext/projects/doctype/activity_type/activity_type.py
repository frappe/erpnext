# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.document import Document

class ActivityType(Document):
	
	def on_trash(self):
		self.validate_manufacturing_type()
		
	def validate_manufacturing_type(self):
		if self.activity_type == 'Manufacturing':
			frappe.throw(_("Activity Type 'Manufacturing' cannot be deleted."))