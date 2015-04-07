# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class ActivityCost(Document):
	def validate(self):
		self.set_title()
		self.check_unique()
		
	def set_title(self):
		self.title = _("{0} for {1}").format(self.employee_name, self.activity_type)
		
	def check_unique(self):
		if frappe.db.exists({ "doctype": "Activity Cost", "employee": self.employee, "activity_type": self.activity_type }):
			frappe.throw(_("Activity Cost exists for Employee {0} against Activity Type {1}")
				.format(self.employee, self.activity_type))
