# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class ExerciseType(Document):
	def autoname(self):
		if self.difficulty_level:
			self.name = ' - '.join(filter(None, [self.exercise_name, self.difficulty_level]))
		else:
			self.name = self.exercise_name

