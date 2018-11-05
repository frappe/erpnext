# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document

class QualityAction(Document):
	def validate(self):
		status_flag = ''
		for value in self.description:
			if value.resolution == None:
				value.status = 'Open'
				status_flag = 'Under Review'
			else:
				value.status = 'Close'
		if status_flag == 'Under Review':
			self.status = 'Under Review'
		else:
			self.status = 'Close'