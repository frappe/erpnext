# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import webnotes

test_records = []

# from webnotes.model.doc import Document
# from webnotes.model.code import get_obj
# webnotes.conn.sql = webnotes.conn.sql
# 
# class TestSalaryManager(unittest.TestCase):
# 	def setUp(self):
# 		webnotes.conn.begin()
# 		for rec in [des1, dep1, branch1, grade1, comp1, emp1, emp2]:
# 			rec.save(1)
# 					
# 		ss1[0].employee = emp1.name
# 		for s in ss1: s.save(1)
# 		for s in ss1[1:]:
# 			webnotes.conn.sql("update `tabSalary Structure Earning` set parent = '%s' where name = '%s'" % (ss1[0].name, s.name))
# 			webnotes.conn.sql("update `tabSalary Structure Deduction` set parent = '%s' where name = '%s'" % (ss1[0].name, s.name))
# 			
# 		
# 		ss2[0].employee = emp2.name
# 		for s in ss2: s.save(1)		
# 		for s in ss2[1:]:
# 			webnotes.conn.sql("update `tabSalary Structure Earning` set parent = '%s' where name = '%s'" % (ss2[0].name, s.name))
# 			webnotes.conn.sql("update `tabSalary Structure Deduction` set parent = '%s' where name = '%s'" % (ss2[0].name, s.name))
# 			
# 		sman.save()
# 		self.sm = get_obj('Salary Manager')	
# 		leave.save(1)
# 		self.sm.create_sal_slip()
# 		
# 	def test_creation(self):
# 		ssid = webnotes.conn.sql("""
# 			select name, department 
# 			from `tabSalary Slip` 
# 			where month = '08' and fiscal_year='2011-2012'""")
# 
# 		self.assertTrue(len(ssid)==1)
# 		self.assertTrue(ssid[0][1] == 'dep1')
# 		
# 		
# 	def test_lwp_calc(self):
# 		ss = webnotes.conn.sql("""
# 			select payment_days
# 			from `tabSalary Slip` 
# 			where month = '08' and fiscal_year='2011-2012' and employee = '%s'
# 		""" % emp1.name)
# 		
# 		self.assertTrue(ss[0][0]==27)
# 		
# 	def test_net_pay(self):
# 		ss = webnotes.conn.sql("""
# 			select rounded_total 
# 			from `tabSalary Slip` 
# 			where month = '08'
# 			and fiscal_year='2011-2012' and employee = '%s'""" % emp1.name)
# 		self.assertTrue(ss[0][0]==67)
# 
# 	def test_submit(self):
# 		self.sm.submit_salary_slip()
# 		ss = webnotes.conn.sql("""
# 			select docstatus 
# 			from `tabSalary Slip` 
# 			where month = '08'
# 			and fiscal_year='2011-2012' and employee = '%s'""" % emp1.name)
# 		self.assertTrue(ss[0][0]==1)
# 		
# 	def tearDown(self):
# 		webnotes.conn.rollback()
# 		
# #--------------------------------------------
# # test data
# #--------------------------------------------
# des1 = Document(fielddata={
# 	'name':'des1',
# 	'doctype':'Designation',
# 	'designation_name':'des1'
# })
# 
# dep1 = Document(fielddata={
# 	'name':'dep1',
# 	'doctype':'Department',
# 	'department_name' : 'dep1'
# })
# 
# branch1 = Document(fielddata={
# 	'name':'branch1',
# 	'doctype':'Branch',
# 	'branch' : 'branch1'
# })
# 
# comp1 = Document(fielddata={
# 	'name':'comp1',
# 	'doctype':'Company',
# 	'abbr':'c1',
# 	'company_name' : 'comp1'
# })
# 
# grade1 = Document(fielddata={
# 	'name':'grade1',
# 	'doctype':'Grade',
# 	'grade_name' : 'grade1'	
# })
# 	
# emp1 = Document(fielddata={
# 	'doctype':'Employee',
# 	'employee_number':'emp1',
# 	'department':'dep1',
# 	'designation':'des1',
# 	'branch' : 'branch1',
# 	'company':'comp1',
# 	'grade':'grade1',
# 	'naming_series':'EMP/',
# 	'status':'Active',
# 	'docstatus':0,
# 	'employee_name':'emp1'
# })
# 
# emp2 = Document(fielddata={
# 	'doctype':'Employee',
# 	'employee_number':'emp2',
# 	'department':'dep1',
# 	'designation':'des2',
# 	'branch' : 'branch1',
# 	'company':'comp1',
# 	'naming_series':'EMP/',
# 	'grade':'grade1',
# 	'status':'Active',
# 
# })
# 
# ss1 = [
# 	Document(fielddata={
# 		'doctype':'Salary Structure',
# 		'docstatus':0,
# 		'employee':'emp1',
# 		'is_active':'Yes',
# 		'department': 'dep1',
# 		'designation' : 'des1',
# 		'employee_name': 'emp1'
# 	}),
# 	Document(fielddata={
# 		'parenttype':'Salary Structure',
# 		'parentfield':'earning_details',
# 		'doctype':'Salary Structure Earning',
# 		'e_type' : 'Basic',
# 		'depend_on_lwp':1,
# 		'modified_value':100
# 	}),
# 	Document(fielddata={
# 		'parenttype':'Salary Structure',
# 		'parentfield':'earning_details',
# 		'doctype':'Salary Structure Deduction',
# 		'd_type':'TDS',
# 		'd_modified_amt':20
# 	})
# ]
# 
# ss2 = [
# 	Document(fielddata={
# 		'doctype':'Salary Structure',
# 		'is_active':'Yes',
# 		'docstatus':0,
# 	}),
# 	Document(fielddata={
# 		'parenttype':'Salary Structure',
# 		'parentfield':'deduction_details',
# 		'doctype':'Salary Structure Earning',
# 		'e_type' : 'Basic',
# 		'modified_value':100
# 	}),
# 	Document(fielddata={
# 		'parenttype':'Salary Structure',
# 		'parentfield':'deduction_details',
# 		'doctype':'Salary Structure Deduction',
# 		'd_type':'TDS',
# 		'd_modified_amt':20
# 	})
# ]
# 
# sman = Document(fielddata={
# 		'name':'Salary Manager',
# 		'doctype':'Salary Manager',
# 		'company': 'comp1',
# 		'department':'dep1',
# 		'designation':'des1',
# 		'month': '08',
# 		'fiscal_year':'2011-2012'
# 	})
# 	
# leave = Document(fielddata = {
# 		'doctype':'Leave Application',
# 		'employee':'emp1',
# 		'from_date':'2011-08-12',
# 		'to_date':'2011-08-15',
# 		'total_leave_days':'4',
# 		'leave_type':'Leave Without Pay',
# 		'docstatus':1
# 	})
