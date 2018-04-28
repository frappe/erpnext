# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

class EmployeeGrade(Document):
	def validate(self):
		self.validate_level()
	
	def validate_level(self):
		if self.max_level <=0 :
			frappe.throw(_("Max level Must have value bigger than 0"))

    
