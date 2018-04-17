# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate
from frappe.model.document import Document
from erpnext.hr.doctype.leave_allocation.leave_allocation import get_carry_forwarded_leaves

class CompensatoryLeaveRequest(Document):
	def validate_present(self):
		pass

	def validate(self):
		self.validate_dates()
		self.validate_overlap()

	def on_submit(self):
		if not self.leave_type:
			frappe.throw(_("Please select a leave type to submit the request"))
		else:
			company = frappe.db.get_value("Employee", self.employee, "company")
			leave_period = self.get_leave_period(company)
			if leave_period:
				max_leaves_allowed = frappe.db.get_value("Leave Type", self.leave_type, "max_leaves_allowed")
				self.validate_leave_allocation_days(leave_period, max_leaves_allowed)
				self.create_leave_allocation(leave_period, max_leaves_allowed)

	def create_leave_allocation(self, leave_period, max_leaves_allowed):
		leave_allocated = get_leave_allocation_for_period(self.employee, self.leave_type, leave_period[0].from_date, leave_period[0].to_date)
		leave_alloc_balance = max_leaves_allowed - leave_allocated
		if leave_alloc_balance > 0:
			is_carry_forward = frappe.db.get_value("Leave Type", self.leave_type, "is_carry_forward")
			print "is_carry_forward: ", is_carry_forward
			allocation = frappe.new_doc("Leave Allocation")
			allocation.employee = self.employee
			allocation.employee_name = self.employee_name
			allocation.leave_type = self.leave_type
			allocation.from_date = self.work_from_date
			allocation.to_date = self.work_end_date
			allocation.new_leaves_allocated = leave_alloc_balance
			allocation.total_leaves_allocated = leave_alloc_balance
			allocation.compensatory_request = self.name
			allocation.description = self.reason
			if is_carry_forward == 1:
				allocation.carry_forward = True
			allocation.save(ignore_permissions = True)
			allocation.submit()
		else:
			frappe.throw(_("Maximum of leave allocation exceed"))


	def get_leave_period(self, company):
		return frappe.db.sql("""
			select name, from_date, to_date
			from `tabLeave Period`
			where company=%(company)s and is_active=1
				and (from_date between %(from_date)s and %(to_date)s
					or to_date between %(from_date)s and %(to_date)s
					or (from_date < %(from_date)s and to_date > %(to_date)s))
		""", {
			"from_date": self.work_from_date,
			"to_date": self.work_end_date,
			"company": company
		}, as_dict=1)

	def validate_dates(self):
		date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")
		if getdate(self.work_from_date) >= getdate(self.work_end_date):
			frappe.throw(_("Work end date can not be equal or less than from date"))
		elif date_of_joining and getdate(self.work_from_date) < getdate(date_of_joining):
			frappe.throw(_("Work from date can not be less than employee's joining date"))

	def validate_overlap(self):
		if not self.name:
			# hack! if name is null, it could cause problems with !=
			self.name = "New Compensatory Leave Request"

		c_leave_request = frappe.db.sql("""
			select name
			from `tabCompensatory Leave Request`
			where employee = %(employee)s and docstatus < 2
			and (work_from_date between %(work_from_date)s and %(work_end_date)s
				or work_end_date between %(work_from_date)s and %(work_end_date)s
				or (work_from_date < %(work_from_date)s and work_end_date > %(work_end_date)s))
			and name != %(name)s""", {
				"employee": self.employee,
				"work_from_date": self.work_from_date,
				"work_end_date": self.work_end_date,
				"name": self.name
			}, as_dict = 1)

		if c_leave_request:
			self.throw_overlap_error(c_leave_request[0].name)

	def throw_overlap_error(self, c_leave_request):
		msg = _("Employee {0} has already requested for Compensatory Leave between {1} and {2} : ").format(self.employee,
			formatdate(self.work_from_date), formatdate(self.work_end_date)) \
			+ """ <b><a href="#Form/Compensatory Leave Request/{0}">{0}</a></b>""".format(c_leave_request)
		frappe.throw(msg)

	def validate_leave_allocation_days(self, leave_period, max_leaves_allowed):
		leave_allocated = get_leave_allocation_for_period(self.employee, self.leave_type, leave_period[0].from_date, leave_period[0].to_date)
		if leave_allocated >= max_leaves_allowed:
			frappe.throw(_("Employee {0} has already allocated thier maximum of {1}").format(self.employee, max_leaves_allowed))

def get_leave_allocation_for_period(employee, leave_type, from_date, to_date):
	leave_allocated = 0
	leave_allocations = frappe.db.sql("""
		select employee, leave_type, from_date, to_date, total_leaves_allocated
		from `tabLeave Allocation`
		where employee=%(employee)s and leave_type=%(leave_type)s
			and docstatus=1
			and (from_date between %(from_date)s and %(to_date)s
				or to_date between %(from_date)s and %(to_date)s
				or (from_date < %(from_date)s and to_date > %(to_date)s))
	""", {
		"from_date": from_date,
		"to_date": to_date,
		"employee": employee,
		"leave_type": leave_type
	}, as_dict=1)

	if leave_allocations:
		for leave_alloc in leave_allocations:
			leave_allocated += leave_alloc.total_leaves_allocated

	return leave_allocated
