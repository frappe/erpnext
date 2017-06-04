# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

class Grade(Document):
	def validate(self):
		pass
		#self.validate_grade_level()
	def validate_grade_level(self):
		other_grade = frappe.get_list("Grade", fields=["name"], filters={"grade_level": self.grade_level}, ignore_permissions=True)
		if other_grade :
			if other_grade[0].name != self.name:
				frappe.throw(_('Grade Level already taken ')+other_grade[0].name)

	def make_earn_ded_table(self):
			self.make_table('Earning Type','earnings','Salary Structure Earning')
			self.make_table('Deduction Type','deductions', 'Salary Structure Deduction')

	def make_table(self, doct_name, tab_fname, tab_name):
		list1 = frappe.db.sql("select name from `tab%s` where docstatus != 2" % doct_name)
		for li in list1:
			child = self.append(tab_fname, {})
			if(tab_fname == 'earnings'):
				child.e_type = cstr(li[0])
				child.modified_value = 0
			elif(tab_fname == 'deductions'):
				child.d_type = cstr(li[0])
				child.d_modified_amt = 0

def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user
	if u'Employee' in frappe.get_roles(user) and not u'HR Manager' in frappe.get_roles(user)and not u'HR User' in frappe.get_roles(user) :
		employee = frappe.get_doc('Employee',{'user_id' : user} )

		return """
			tabGrade.name ='{employee}'
			""".format( employee= employee.grade or 0 )
