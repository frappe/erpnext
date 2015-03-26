# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe import _
from frappe.model.document import Document

class ActivityCost(Document):
	def validate(self):
		self.set_title()
		
	def set_title(self):
		self.title = _("{0} for {1}").format(self.employee_name, self.activity_type)
