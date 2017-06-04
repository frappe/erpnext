# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class EndofServiceAward(Document):
	def get_salary(self,employee):
		result =frappe.db.sql("select net_pay from `tabSalary Slip` where employee='{0}' order by creation desc limit 1".format(employee))
		if result:
			return result[0][0]
		else:
			frappe.throw("لا يوجد قسيمة راتب لهذا الموظف")

		


