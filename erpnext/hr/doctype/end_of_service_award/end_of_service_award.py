# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class EndofServiceAward(Document):

	def validate(self):
		if self.workflow_state:
			if "Rejected" in self.workflow_state:
				self.docstatus = 1
				self.docstatus = 2
		# frappe.throw(str(self.months))

	def get_salary(self,employee):
		result =frappe.db.sql("select net_pay from `tabSalary Slip` where employee='{0}' order by creation desc limit 1".format(employee))
		if result:
			return result[0][0]
		else:
			frappe.throw("لا يوجد قسيمة راتب لهذا الموظف")

		


