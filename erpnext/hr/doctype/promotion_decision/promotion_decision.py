# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils import flt, getdate
from frappe.model.document import Document

class PromotionDecision(Document):
	def validate(self):
		self.check_total_points()
		self.validate_dates()
		self.validate_contest()

	def check_total_points(self):
		if self.promotion_type =="By Comparison":
			total_points = 0
			for d in self.get("goals"):
				total_points += int(d.per_weightage or 0)
			if cint(total_points) != 100:
				frappe.throw(_("Sum of points for all goals should be 100. It is {0}").format(total_points))


	def validate_contest(self):
		if self.promotion_type == "By Contest":
			if not self.contest_id or not self.contest_result :
				frappe.throw(_("Enter Contest Information"))


	def before_submit(self):
		self.validate_dates()
		self.validate_contest()

	def on_submit(self):
		self.insert_work_history()

	def insert_work_history(self):
		employee = frappe.get_doc('Employee',{'name' : self.employee})
		# salary_structer_list = frappe.get_list("Salary Structure", fields=["name"],filters ={'employee' : employee.name,'is_active':'Yes'})
		# if salary_structer_list:
		# 	salary_structer = frappe.get_doc('Salary Structure Employee',{'employee' : employee.name,'is_active':'Yes'} )
		# 	salary_structer.grade =self.new_grade if self.new_grade else salary_structer.grade
		# 	salary_structer.main_payment =self.main_payment if self.main_payment else salary_structer.main_payment
		# 	salary_structer.total_earning =self.total_earning if self.total_earning else salary_structer.total_earning
		# 	salary_structer.total_deduction =self.total_deduction if self.total_deduction else salary_structer.total_deduction
		# 	salary_structer.net_pay =self.net_pay if self.net_pay else salary_structer.net_pay

		# 	# doc.set("packed_items", [])
		# 	if self.earnings != []:
		# 		salary_structer.set("earnings", [])
		# 		for d in self.earnings:
		# 			salary_structer.append("earnings", d)
		# 	if self.deductions != [] :
		# 		salary_structer.set("deductions", [])
		# 		for d in self.deductions:
		# 			salary_structer.append("deductions", d)

		# 	salary_structer.save(ignore_permissions=True)
		# else :
		# 	frappe.throw(_("Add Salary Structer for Employee")+"<a href='#List/Salary Structure'>"+_("Salary Structure")+"</a>")

		# old_jo = employee.job_opening
		# jo_list = frappe.get_list("Job Opening", fields=["name"],filters ={'name' : employee.job_opening})
		# if jo_list:
		# 	jo = frappe.get_doc('Job Opening',{'name' : employee.job_opening} )
		# 	jo.status ='Open'
		# 	jo.save()


		old_work_start_date = employee.date_of_joining
		employee.grade = self.new_grade if self.new_grade else employee.grade
		employee.employment_type = self.new_employment_type if self.new_employment_type else employee.employment_type
		employee.department=self.new_department if self.new_department else employee.department
		employee.designation = self.new_designation if self. new_designation else employee.designation
		employee.branch=self.new_branch if self.new_branch else employee.branch
		# employee.job_opening = self.job_opening if self.job_opening else employee.job_opening
		employee.date_of_joining= self.due_date if self.due_date else employee.date_of_joining
		# employee.work_start_date_hijri = self.due_date if self.due_date else employee.work_start_date
		# employee.scheduled_confirmation_date = self.due_date if self.due_date else employee.scheduled_confirmation_date
		# employee.scheduled_confirmation_date_hijri = self.due_date if self.due_date else employee.scheduled_confirmation_date
		employee.save()

		# jo1_list = frappe.get_list("Job Opening", fields=["name"],filters ={'name' : self.job_opening})
		# if jo1_list:
		# 	jo1 = frappe.get_doc('Job Opening',{'name' : self.job_opening} )
		# 	jo1.status ='Closed'
		# 	jo1.save()

		old_work = frappe.new_doc(u'Employee Internal Work History',employee,u'internal_work_history')
		old_work.update(
			{
				"type":"Promotion",
				"branch": self.branch,
				"department":  self.department,
				"designation":self.designation,
				"grade_old": self.grade,
				# "job_opening":old_jo,
				"employment_type":self.employment_type,
				"new_branch": self.new_branch,
				"new_department":  self.new_department,
				"new_designation":self.new_designation,
				"new_grade": self.new_grade,
				"new_employment_type":self.new_employment_type,
				# "new_job_opening":self.job_opening,
				"work_start_date":old_work_start_date,
				# "from_date": employee.scheduled_confirmation_date,
				"to_date": self.due_date,
				"administrative_decision":self.name
			}
		)
		old_work.insert()



	def validate_dates(self):
		if getdate(self.due_date) > getdate(self.commencement_date):
			frappe.throw(_("Commencement date can not be less than Due date"))

	def get_child_table(self):
		if self.new_grade:
			doc_a = frappe.get_doc("Grade",self.new_grade)
			self.main_payment = doc_a.main_payment
			# self.total_earning = doc_a.total_earning
			# self.total_deduction = doc_a.total_deduction
			# self.net_pay = doc_a.net_pay
			self.accommodation_from_company = doc_a.accommodation_from_company
			self.accomodation_percentage = doc_a.accomodation_percentage
			self.accommodation_value = doc_a.accommodation_value
			# self.accommodation_value = doc_a.accommodation_value
			self.transportation_costs = doc_a.transportation_costs
			# list1=doc_a.get("earnings")
			# list2=doc_a.get("deductions")
			# for t in list1:
			# 	child = self.append('earnings', {})
			# 	child.e_type = t.e_type
			# 	child.depend_on_lwp = t.depend_on_lwp
			# 	child.modified_value = t.modified_value
			# 	child.e_percentage = t.e_percentage
			# for t in list2:
			# 	child = self.append('deductions', {})
			# 	child.d_type = t.d_type
			# 	child.based_on_total = t.based_on_total
			# 	child.d_modified_amt = t.d_modified_amt
			# 	child.d_percentage = t.d_percentage
			# 	child.depend_on_lwp = t.depend_on_lwp
			return "done"
		else :
			return "no grade"
