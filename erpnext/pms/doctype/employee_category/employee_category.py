# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class EmployeeCategory(Document):
	def validate(self):
		self.check_duplicate_designation_entry()
	def check_duplicate_designation_entry(self):
		for i in self.get('items'):
			designation = frappe.db.sql("""
				SELECT 
					parent,designation
				FROM 
					`tabEmployee Category Group`
				WHERE 
					designation = '{}'
			""".format(i.designation),as_dict=True)
			for d in designation:
				if d.parent != self.employee_category:
					frappe.throw('Designation {0} already exist under {1} category'.format(d.designation,d.parent))
			
