# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, flt
from webnotes import msgprint
	
class DocType:
	def __init__(self, doc, doclist):
		self.doc, self.doclist = doc, doclist
		
	def validate(self):
		self.validate_new_leaves_allocated_value()
		self.check_existing_leave_allocation()
		self.validate_new_leaves_allocated()
		
	def on_update_after_submit(self):
		self.validate_new_leaves_allocated_value()
		self.validate_new_leaves_allocated()

	def on_update(self):
		self.get_total_allocated_leaves()
		
	def on_cancel(self):
		self.check_for_leave_application()
		
	def validate_new_leaves_allocated_value(self):
		"""validate that leave allocation is in multiples of 0.5"""
		if flt(self.doc.new_leaves_allocated) % 0.5:
			guess = round(flt(self.doc.new_leaves_allocated) * 2.0) / 2.0
			
			msgprint("""New Leaves Allocated should be a multiple of 0.5.
				Perhaps you should enter %s or %s""" % (guess, guess + 0.5),
				raise_exception=1)
		
	def check_existing_leave_allocation(self):
		"""check whether leave for same type is already allocated or not"""
		leave_allocation = webnotes.conn.sql("""select name from `tabLeave Allocation`
			where employee=%s and leave_type=%s and fiscal_year=%s and docstatus=1""",
			(self.doc.employee, self.doc.leave_type, self.doc.fiscal_year))
		if leave_allocation:
			msgprint("""%s is already allocated to Employee: %s for Fiscal Year: %s.
				Please refere Leave Allocation: \
				<a href="#Form/Leave Allocation/%s">%s</a>""" % \
				(self.doc.leave_type, self.doc.employee, self.doc.fiscal_year,
				leave_allocation[0][0], leave_allocation[0][0]), raise_exception=1)
			
	def validate_new_leaves_allocated(self):
		"""check if Total Leaves Allocated >= Leave Applications"""
		self.doc.total_leaves_allocated = flt(self.doc.carry_forwarded_leaves) + \
			flt(self.doc.new_leaves_allocated)
		leaves_applied = self.get_leaves_applied(self.doc.fiscal_year)
		if leaves_applied > self.doc.total_leaves_allocated:
			expected_new_leaves = flt(self.doc.new_leaves_allocated) + \
				(leaves_applied - self.doc.total_leaves_allocated)
			msgprint("""Employee: %s has already applied for %s leaves.
				Hence, New Leaves Allocated should be atleast %s""" % \
				(self.doc.employee, leaves_applied, expected_new_leaves),
				raise_exception=1)
		
	def get_leave_bal(self, prev_fyear):
		return self.get_leaves_allocated(prev_fyear) - self.get_leaves_applied(prev_fyear)
		
	def get_leaves_applied(self, fiscal_year):
		leaves_applied = webnotes.conn.sql("""select SUM(ifnull(total_leave_days, 0))
			from `tabLeave Application` where employee=%s and leave_type=%s
			and fiscal_year=%s and docstatus=1""", 
			(self.doc.employee, self.doc.leave_type, fiscal_year))
		return leaves_applied and flt(leaves_applied[0][0]) or 0

	def get_leaves_allocated(self, fiscal_year):
		leaves_allocated = webnotes.conn.sql("""select SUM(ifnull(total_leaves_allocated, 0))
			from `tabLeave Allocation` where employee=%s and leave_type=%s
			and fiscal_year=%s and docstatus=1 and name!=%s""",
			(self.doc.employee, self.doc.leave_type, fiscal_year, self.doc.name))
		return leaves_allocated and flt(leaves_allocated[0][0]) or 0
	
	def allow_carry_forward(self):
		"""check whether carry forward is allowed or not for this leave type"""
		cf = webnotes.conn.sql("""select is_carry_forward from `tabLeave Type` where name = %s""",
			self.doc.leave_type)
		cf = cf and cint(cf[0][0]) or 0
		if not cf:
			webnotes.conn.set(self.doc,'carry_forward',0)
			msgprint("Sorry! You cannot carry forward %s" % (self.doc.leave_type),
				raise_exception=1)

	def get_carry_forwarded_leaves(self):
		if self.doc.carry_forward:
			self.allow_carry_forward()
		prev_fiscal_year = webnotes.conn.sql("""select name from `tabFiscal Year` 
			where year_start_date = (select date_add(year_start_date, interval -1 year) 
				from `tabFiscal Year` where name=%s) 
			order by name desc limit 1""", self.doc.fiscal_year)
		prev_fiscal_year = prev_fiscal_year and prev_fiscal_year[0][0] or ''
		prev_bal = 0
		if prev_fiscal_year and cint(self.doc.carry_forward) == 1:
			prev_bal = self.get_leave_bal(prev_fiscal_year)
		ret = {
			'carry_forwarded_leaves': prev_bal,
			'total_leaves_allocated': flt(prev_bal) + flt(self.doc.new_leaves_allocated)
		}
		return ret

	def get_total_allocated_leaves(self):
		leave_det = self.get_carry_forwarded_leaves()
		webnotes.conn.set(self.doc,'carry_forwarded_leaves',flt(leave_det['carry_forwarded_leaves']))
		webnotes.conn.set(self.doc,'total_leaves_allocated',flt(leave_det['total_leaves_allocated']))

	def check_for_leave_application(self):
		exists = webnotes.conn.sql("""select name from `tabLeave Application`
			where employee=%s and leave_type=%s and fiscal_year=%s and docstatus=1""",
			(self.doc.employee, self.doc.leave_type, self.doc.fiscal_year))
		if exists:
			msgprint("""Cannot cancel this Leave Allocation as \
				Employee : %s has already applied for %s. 
				Please check Leave Application: \
				<a href="#Form/Leave Application/%s">%s</a>""" % \
				(self.doc.employee, self.doc.leave_type, exists[0][0], exists[0][0]))
			raise Exception

