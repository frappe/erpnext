# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from umalqurra.hijri_date import HijriDate
import datetime
import json

class MayConcernLetter(Document):
	


	def get_hijry(self):

		datee = datetime.datetime.strptime(frappe.utils.today(), "%Y-%m-%d")
		um = HijriDate(datee.year,datee.month,datee.day,gr=True)
		return str('هـ'+str(int(um.year))+str(um.month_name) + str(int(um.day)))



	def validate(self):
		self.fieldsvalidate()
		self.hijry=self.get_hijry()
		self.salary=self.get_salary()
		if self.workflow_state:
			if "Rejected" in self.workflow_state:
			    self.docstatus = 1
			    self.docstatus = 2

	def fieldsvalidate(self):
		if not self.employee_name:
			frappe.throw('الرجاء ادخال اسم الموظف بالعربية حتي يظهر بالطباعة')

		if not self.employee_name_english:
			frappe.throw('الرجاء ادخال اسم الموظف بالانجليزية حتي يظهر بالطباعة')
		
		if not self.designation:
			frappe.throw('الرجاء ادخال المسمى الوظيفي بالعربية حتي يظهر بالطباعة')
		

		if not self.designation_name_english:
			frappe.throw('الرجاء ادخال المسمى الوظيفي بالانجليزية حتي يظهر بالطباعة')
		

		if not self.nationality:
			frappe.throw('الرجاء ادخال جنسية الموظف  بالعربية حتي يظهر بالطباعة')


		if not self.nationality_english:
			frappe.throw('الرجاء ادخال جنسية الموظف بالانجليزية حتي يظهر بالطباعة')


		if not self.civil_id:
			frappe.throw('الرجاء ادخال الرقم القومي للموظف حتي يظهر بالطباعة')
		

		if not self.department:
			frappe.throw(' الرجاء ادخال قسم الموظف حتي يظهر بالطباعة')




	def get_salary(self):
		if self.salary_selection=='Total Salary' or self.salary_selection=='Basic Salary' or self.salary_selection=='Detailed Salary'   :
			doc = frappe.new_doc("Salary Slip")
			doc.salary_slip_based_on_timesheet="0"

			doc.payroll_frequency= "Monthly"
			doc.start_date="2017-11-01"
			doc.end_date="2017-11-29"
			doc.employee= str(self.employee)
			doc.employee_name=str(self.employee_name)
			doc.company= "Tawari"
			doc.posting_date= "2017-10-01"
			
			doc.insert(ignore_permissions=True)


			result =doc.gross_pay
			self.gross_pay=result
			
			for earning in doc.earnings:
				if earning.salary_component =='Basic':
					self.basic = str(earning.amount)
				if earning.salary_component =='Housing':
					self.housing = str(earning.amount)
				if earning.salary_component =='Transportation':
					self.transportation = str(earning.amount)
				if earning.salary_component =='Communication':
					self.communication = str(earning.amount)

			doc.delete()

					

			if result:
			    return result
			else:
			    frappe.msgprint("لا يوجد قسيمة راتب لهذا الموظف")
			    self.salary_selection='No salary'
			    return '0'


		# elif self.salary_selection=='Basic Salary':
		# 	result= frappe.get_list('Salary Slip', filters={'employee': self.employee})
		# 	if result:
		# 		doc = frappe.get_doc('Salary Slip',result[0])
		# 		for earning in doc.earnings:
		# 			if earning.salary_component =='Basic':
		# 				return str(earning.amount)
		# 	else:
		# 	    frappe.msgprint("لا يوجد قسيمة راتب لهذا الموظف")
		# 	    self.salary_selection='No salary'
		# 	    return '0'

				



def get_permission_query_conditions(user):
	pass
	# if not user: user = frappe.session.user
	# employees = frappe.get_list("Employee", fields=["name"], filters={'user_id': user}, ignore_permissions=True)
	# if employees:
	# 	query = ""
	# 	employee = frappe.get_doc('Employee', {'name': employees[0].name})
		
	# 	if u'Employee' in frappe.get_roles(user):
	# 		if query != "":
	# 			query+=" or "
	# 		query+=""" employee = '{0}'""".format(employee.name)
	# 	return query
