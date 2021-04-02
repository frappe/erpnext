# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class WorkCompetency(Document):
	def get_employee_category(self):
		self.set('employee_category_item', [])
		data = frappe.db.sql("""
			SELECT
				employee_category
			FROM 
				`tabEmployee Category`;
		""",as_dict=True)
		if not data:
			frappe.throw('There are No Employee Category defined')
		for d in data:
			row = self.append('employee_category_item',{})
			row.update(d)
		return

