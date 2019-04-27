# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
from frappe.utils import today

class QualityGoal(Document):

	def after_insert(self):
		if self.is_new:
			self.revision = 0
		else:
			self.revision += 1

		self.revised_on = today()
