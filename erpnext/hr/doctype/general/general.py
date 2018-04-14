# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
	comma_or, get_fullname, add_years, add_months, add_days, nowdate, get_first_day, get_last_day
from erpnext.hr.doctype.leave_application.leave_application import get_monthly_accumulated_leave
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on


class General(Document):

	def get_leaves_balances(self, annual, emergency):
		self.annual_leave_balance = get_monthly_accumulated_leave(nowdate(), nowdate(), annual, self.employee, for_report=True)
		self.emergency_leave_balance = get_leave_balance_on(self.employee, emergency, nowdate())

@frappe.whitelist(allow_guest=True)
def get_sal_slip(employee,arabic_name):

	doc = frappe.new_doc("Salary Slip")
	doc.salary_slip_based_on_timesheet="0"

	doc.payroll_frequency= "Monthly"
	doc.start_date=get_first_day(getdate(nowdate()))
	doc.end_date=get_last_day(getdate(nowdate()))
	doc.employee= employee
	doc.employee_name=arabic_name
	doc.company= "Tawari"
	doc.posting_date= get_first_day(getdate(nowdate()))
	
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	total_deduction = doc.total_deduction if doc.total_deduction else 0
	gross_pay = doc.gross_pay if doc.gross_pay else 0
	net_pay = doc.net_pay if doc.net_pay else 0

	for earning in doc.earnings:
		basic = {'salary_component': 'Basic', 'amount': earning.amount } if earning.salary_component =='Basic' else 0
			
		housing = {'salary_component': 'Housing', 'amount': earning.amount } if earning.salary_component =='Housing' else 0
			
		transportation = {'salary_component': 'Transportation', 'amount': earning.amount } if earning.salary_component =='Transportation' else 0
			
		communication = {'salary_component': 'Communication', 'amount': earning.amount } if earning.salary_component =='Communication' else 0
			


	for deductions in doc.deductions:
		if deductions.salary_component =='GOSI':
			gosi = [{'salary_component': 'GOSI', 'amount': deductions.amount }]
		else:
			gosi = []
	doc.delete()

	list_earning=[basic,housing,transportation,communication]
	list1= [total_deduction,gross_pay,net_pay,gosi,list_earning]


	return list1


			





