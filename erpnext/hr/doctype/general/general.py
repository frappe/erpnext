# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class General(Document):
	pass

@frappe.whitelist(allow_guest=True)
def get_sal_slip(employee,arabic_name):

	doc = frappe.new_doc("Salary Slip")
	doc.salary_slip_based_on_timesheet="0"

	doc.payroll_frequency= "Monthly"
	doc.start_date="2017-11-01"
	doc.end_date="2017-11-29"
	doc.employee= employee
	doc.employee_name=arabic_name
	doc.company= "Tawari"
	doc.posting_date= "2017-10-01"
	
	doc.insert(ignore_permissions=True)


	total_deduction =doc.total_deduction
	gross_pay =doc.gross_pay
	net_pay =doc.net_pay

	for earning in doc.earnings:
		if earning.salary_component =='Basic':
			basic = {'salary_component': 'Basic', 'amount': earning.amount }
		if earning.salary_component =='Housing':
			housing = {'salary_component': 'Housing', 'amount': earning.amount }
		if earning.salary_component =='Transportation':
			transportation = {'salary_component': 'Transportation', 'amount': earning.amount }
		if earning.salary_component =='Communication':
			communication = {'salary_component': 'Communication', 'amount': earning.amount }


	for deductions in doc.deductions:
		if deductions.salary_component =='GOSI':
			gosi = [{'salary_component': 'GOSI', 'amount': deductions.amount }]

	doc.delete()

	list_earning=[basic,housing,transportation,communication]
	list1= [total_deduction,gross_pay,net_pay,gosi,list_earning]


	return list1


			





