# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, cstr, add_days, date_diff, getdate, ceil
from frappe.model.document import Document
from erpnext.hr.utils import validate_overlap, get_employee_leave_policy
from frappe.utils.background_jobs import enqueue
from six import iteritems

class LeavePeriod(Document):
	# def get_employees(self, args):
	# 	conditions, values = [], []
	# 	for field, value in iteritems(args):
	# 		if value:
	# 			conditions.append("{0}=%s".format(field))
	# 			values.append(value)

	# 	condition_str = " and " + " and ".join(conditions) if len(conditions) else ""

	# 	employees = frappe._dict(frappe.db.sql("select name, date_of_joining from tabEmployee where status='Active' {condition}" #nosec
	# 		.format(condition=condition_str), tuple(values)))

	# 	return employees

	def validate(self):
		self.validate_dates()
		validate_overlap(self, self.from_date, self.to_date, self.company)

	def validate_dates(self):
		if getdate(self.from_date) >= getdate(self.to_date):
			frappe.throw(_("To date can not be equal or less than from date"))


	# def grant_leave_allocation(self, grade=None, department=None, designation=None,
	# 		employee=None, carry_forward=0):
	# 	employee_records = self.get_employees({
	# 		"grade": grade,
	# 		"department": department,
	# 		"designation": designation,
	# 		"name": employee
	# 	})

	# 	if employee_records:
	# 		if len(employee_records) > 20:
	# 			frappe.enqueue(grant_leave_alloc_for_employees, timeout=600,
	# 				employee_records=employee_records, leave_period=self, carry_forward=carry_forward)
	# 		else:
	# 			grant_leave_alloc_for_employees(employee_records, self, carry_forward)
	# 	else:
	# 		frappe.msgprint(_("No Employee Found"))
