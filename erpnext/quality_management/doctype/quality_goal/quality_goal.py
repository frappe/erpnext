# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document

class QualityGoal(Document):

	def validate(self):
		self.revision += 1
		self.revised_on = frappe.utils.today()
