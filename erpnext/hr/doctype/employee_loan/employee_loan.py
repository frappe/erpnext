# -*- coding: utf-8 -*-
# Copyright (c) 2015, Rohit Industries Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import getdate
import frappe
from frappe.model.document import Document
import math

class EmployeeLoan(Document):
	def validate(self):
		self.total_loan = 0
		for i in self.employee_loan_detail:
			#Populate Employee Name from ID
			i.employee_name = frappe.get_doc("Employee", i.employee).employee_name

			#Change values as per the loan amount
			if i.loan_amount != i.emi * i.repayment_period:
				if i.emi%100 !=0:
					i.emi = int(math.ceil(i.emi/100))*100
				i.repayment_period = i.loan_amount/i.emi

			if (i.loan_amount < 0 or i.emi < 0 or i.repayment_period < 0):
				frappe.throw("Loan Amount, EMI and Repayment Period should be greater than ZERO")
				
			#Check Duplicate Employee
			all_employee = []
			for j in self.employee_loan_detail:
				all_employee.append (j.employee)
			if all_employee.count(i.employee)>1:
				frappe.throw(("{0} is entered multiple times").format(i.employee_name))
			
			#Don't allow inactive employees on that date
			emp = frappe.get_doc("Employee", i.employee)
			pd = getdate(self.posting_date)
			rd = getdate(emp.relieving_date)
			if emp.status <> "Active" and rd < pd:
				frappe.throw(("{0} left on {1} hence cannot give advance on {2}").\
					format(i.employee_name, rd, pd))
			self.total_loan += i.loan_amount
	
	def on_update(self):
		#check if the JV is already existing
		chk_jv = frappe.db.sql("""SELECT jv.name FROM `tabJournal Entry` jv, 
			`tabJournal Entry Account` jva WHERE jva.parent = jv.name AND jv.docstatus <> 2 AND
			jva.reference_name = '%s' GROUP BY jv.name"""% self.name, as_list=1)
		
		jv_acc_lst = []
		jv_db_dict = {}
		jv_db_dict.setdefault("account", self.debit_account)
		jv_db_dict.setdefault("debit_in_account_currency", self.total_loan)
		jv_db_dict.setdefault("reference_type", "Employee Loan")
		jv_db_dict.setdefault("reference_name", self.name)
		
		jv_acc_lst.append(jv_db_dict)
		
		jv_cr_dict = {}
		jv_cr_dict.setdefault("account", self.credit_account)
		jv_cr_dict.setdefault("credit_in_account_currency", self.total_loan)
		jv_cr_dict.setdefault("reference_type", "Employee Loan")
		jv_cr_dict.setdefault("reference_name", self.name)
		
		jv_acc_lst.append(jv_cr_dict)
		
		#post JV on saving
		jv = frappe.get_doc({
			"doctype": "Journal Entry",
			"entry_type": "Journal Entry",
			"series": "JV1617",
			"user_remark": "Loan Given against Employee Loan #" + self.name,
			"posting_date": self.posting_date,
			"employment_type": "Accounts Employee",
			"accounts": [jv_db_dict, jv_cr_dict]
			})
		if chk_jv:
			name = chk_jv[0][0]
			jv_exist = frappe.get_doc("Journal Entry", name)
			jv_exist.posting_date = self.posting_date
			jv_exist.user_remark = "Loan Given against Employee Loan #" + self.name
			jv_exist.accounts= []
			jv_exist.append("accounts", jv_cr_dict)
			jv_exist.append("accounts", jv_db_dict)
			jv_exist.save()
			for i in jv_acc_lst:
				jv_exist.append("accounts", i)
			frappe.msgprint('{0}{1}'.format("Update JV# ", jv_exist.name))
		else:
			jv.insert()
			frappe.msgprint('{0}{1}'.format("Created New JV# ", jv.name))
	
	def on_submit(self):
		chk_jv = frappe.db.sql("""SELECT jv.name FROM `tabJournal Entry` jv, 
			`tabJournal Entry Account` jva WHERE jva.parent = jv.name AND jv.docstatus = 0 AND
			jva.reference_name = '%s' GROUP BY jv.name"""% self.name, as_list=1)
		if chk_jv:
			name = chk_jv[0][0]
			jv_exist = frappe.get_doc("Journal Entry", name)
			jv_exist.submit()
			frappe.msgprint('{0}{1}'.format("Submitted JV# ", jv_exist.name))
		
	def on_cancel(self):
		chk_jv = frappe.db.sql("""SELECT jv.name FROM `tabJournal Entry` jv, 
			`tabJournal Entry Account` jva WHERE jva.parent = jv.name AND jv.docstatus = 1 AND
			jva.reference_name = '%s' GROUP BY jv.name"""% self.name, as_list=1)
		if chk_jv:
			name = chk_jv[0][0]
			jv_exist = frappe.get_doc("Journal Entry", name)
			jv_exist.cancel()
			frappe.msgprint('{0}{1}'.format("Cancelled JV# ", jv_exist.name))
