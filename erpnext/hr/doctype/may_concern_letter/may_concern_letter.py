# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
class MayConcernLetter(Document):
	
	def validate(self):
		self.fieldsvalidate()
		self.salary=self.get_salary()

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
		if self.salary_selection=='Total Salary':
			result =frappe.db.sql("select net_pay from `tabSalary Slip` where employee='{0}' and docstatus=1 order by creation desc limit 1".format(self.employee))
			if result:
			    return result[0][0]
			else:
			    frappe.msgprint("لا يوجد قسيمة راتب لهذا الموظف")
			    self.salary_selection='No salary'
			    return '0'
		
		elif self.salary_selection=='Basic Salary':
			result= frappe.get_list('Salary Slip', filters={'employee': self.employee})
			if result:
				doc = frappe.get_doc('Salary Slip',result[0])
				for earning in doc.earnings:
					if earning.salary_component =='Basic':
						return str(earning.amount)
			else:
			    frappe.msgprint("لا يوجد قسيمة راتب لهذا الموظف")
			    self.salary_selection='No salary'
			    return '0'

				

