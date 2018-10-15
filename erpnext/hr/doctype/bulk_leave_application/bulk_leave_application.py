# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class BulkLeaveApplication(Document):
	def create_leave_applications(self):
		if not self.employee:
			frappe.throw(_("Employee is mandatory"))
		for d in self.periods:
			if d.leave_type and d.from_date and d.to_date:
				leave = frappe.new_doc("Leave Application")
				leave.employee = self.employee
				leave.leave_type = d.leave_type
				leave.from_date = d.from_date
				leave.to_date = d.to_date
				leave.half_day = d.half_day
				leave.half_day_date = d.half_day_date
				leave.status = "Approved"
				leave.save()
				leave.submit()