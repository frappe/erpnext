# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class UtilityServices(Document):
	def validate(self):
		self.validate_duplicate()
	
	def validate_duplicate(self):
		result = frappe.db.sql("""select name
								from `tabUtility Services`
								where branch = '{}'
								and name != '{}'
							""".format(self.branch, self.name))
		if result:
			frappe.throw("Utility services for {} branch already exists.".format(self.branch))
		
		for a in self.item:
			result1 = frappe.db.sql("""select name
								from `tabUtility Services Item`
								where consumer_code = '{}'
								and utility_service_type = '{}'
								and parent != '{}'
							""".format(a.consumer_code, a.utility_service_type, self.name))
			if result1:
				frappe.throw("Record already exist with customer code {} and Utility Service {}".format(a.consumer_code, a.utility_service_type))