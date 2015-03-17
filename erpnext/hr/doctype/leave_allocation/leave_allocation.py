# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, flt
from frappe import _
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name

class LeaveAllocation(Document):
	def validate(self):
		self.validate_new_leaves_allocated_value()
		self.check_existing_leave_allocation()
		if not self.total_leaves_allocated:
			self.total_leaves_allocated = self.new_leaves_allocated

		set_employee_name(self)

	def on_update_after_submit(self):
		self.validate_new_leaves_allocated_value()

	def on_update(self):
		self.get_total_allocated_leaves()

	def on_cancel(self):
		self.check_for_leave_application()

	def validate_new_leaves_allocated_value(self):
		"""validate that leave allocation is in multiples of 0.5"""
		if flt(self.new_leaves_allocated) % 0.5:
			frappe.throw(_("Leaves must be allocated in multiples of 0.5"))

	def check_existing_leave_allocation(self):
		"""check whether leave for same type is already allocated or not"""
		leave_allocation = frappe.db.sql("""select name from `tabLeave Allocation`
			where employee=%s and leave_type=%s and fiscal_year=%s and docstatus=1""",
			(self.employee, self.leave_type, self.fiscal_year))
		if leave_allocation:
			frappe.msgprint(_("Leaves for type {0} already allocated for Employee {1} for Fiscal Year {0}").format(self.leave_type,
				self.employee, self.fiscal_year))
			frappe.throw('<a href="#Form/Leave Allocation/{0}">{0}</a>'.format(leave_allocation[0][0]))

	def get_leave_bal(self, prev_fyear):
		return self.get_leaves_allocated(prev_fyear) - self.get_leaves_applied(prev_fyear)

	def get_leaves_applied(self, fiscal_year):
		leaves_applied = frappe.db.sql("""select SUM(ifnull(total_leave_days, 0))
			from `tabLeave Application` where employee=%s and leave_type=%s
			and fiscal_year=%s and docstatus=1""",
			(self.employee, self.leave_type, fiscal_year))
		return leaves_applied and flt(leaves_applied[0][0]) or 0

	def get_leaves_allocated(self, fiscal_year):
		leaves_allocated = frappe.db.sql("""select SUM(ifnull(total_leaves_allocated, 0))
			from `tabLeave Allocation` where employee=%s and leave_type=%s
			and fiscal_year=%s and docstatus=1 and name!=%s""",
			(self.employee, self.leave_type, fiscal_year, self.name))
		return leaves_allocated and flt(leaves_allocated[0][0]) or 0

	def allow_carry_forward(self):
		"""check whether carry forward is allowed or not for this leave type"""
		cf = frappe.db.sql("""select is_carry_forward from `tabLeave Type` where name = %s""",
			self.leave_type)
		cf = cf and cint(cf[0][0]) or 0
		if not cf:
			frappe.db.set(self,'carry_forward',0)
			frappe.throw(_("Cannot carry forward {0}").format(self.leave_type))

	def get_carry_forwarded_leaves(self):
		if self.carry_forward:
			self.allow_carry_forward()
		prev_fiscal_year = frappe.db.sql("""select name from `tabFiscal Year`
			where year_start_date = (select date_add(year_start_date, interval -1 year)
				from `tabFiscal Year` where name=%s)
			order by name desc limit 1""", self.fiscal_year)
		prev_fiscal_year = prev_fiscal_year and prev_fiscal_year[0][0] or ''
		prev_bal = 0
		if prev_fiscal_year and cint(self.carry_forward) == 1:
			prev_bal = self.get_leave_bal(prev_fiscal_year)
		ret = {
			'carry_forwarded_leaves': prev_bal,
			'total_leaves_allocated': flt(prev_bal) + flt(self.new_leaves_allocated)
		}
		return ret

	def get_total_allocated_leaves(self):
		leave_det = self.get_carry_forwarded_leaves()
		frappe.db.set(self,'carry_forwarded_leaves',flt(leave_det['carry_forwarded_leaves']))
		frappe.db.set(self,'total_leaves_allocated',flt(leave_det['total_leaves_allocated']))

	def check_for_leave_application(self):
		exists = frappe.db.sql("""select name from `tabLeave Application`
			where employee=%s and leave_type=%s and fiscal_year=%s and docstatus=1""",
			(self.employee, self.leave_type, self.fiscal_year))
		if exists:
			frappe.msgprint(_("Cannot cancel because Employee {0} is already approved for {1}").format(self.employee,
				self.leave_type))
			frappe.throw('<a href="#Form/Leave Application/{0}">{0}</a>'.format(exists[0][0]))

