# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate

class EmployeeTransfer(Document):
	def validate(self):
		if getdate(self.promotion_date) < getdate():
			frappe.throw("Cannot create promotion for past date")

	def on_submit(self):
		employee = frappe.get_doc("Employee", self.employee)
		for item in self.promotion_details:
			setattr(employee, item.fieldname, item.new)
		employee.save()
