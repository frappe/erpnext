# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document

class QualityMeeting(Document):
	def validate(self):
		problem = ''
		for data in self.minutes:
			if data.status == 'Open':
				problem = 'set'

		if problem == 'set':
			self.status = 'Open'
		else:
			self.status = 'Close'