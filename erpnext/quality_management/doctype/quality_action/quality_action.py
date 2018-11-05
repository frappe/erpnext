# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document

class QualityAction(Document):
	def validate(self):
		for value in self.description:
			if value.resolution == None:
				value.status = 'Open'
				self.status = 'Under Review'
			else:
				value.status = 'Close'
				self.status = 'Closed'