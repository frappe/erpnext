# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document

class QualityReview(Document):
	def validate(self):
		if self.measurable == "Yes":
			if self.goal:
				problem = ''
				for value in self.values:
					if int(value.achieved) < int(value.target):
						problem = 'set'
						break
				if problem == 'set':
					self.action = 'Action Initialised'
				else:
					self.action = 'No Action'
		else:
			if self.goal:
				problem = ''
				for value in self.values:
					if value.yes_no == "No":
						problem = 'set'
				if problem == 'set':
					self.action = 'Action Initialised'
				else:
					self.action = 'No Action'