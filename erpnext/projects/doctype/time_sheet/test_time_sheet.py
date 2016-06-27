# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
import datetime
from frappe.utils import now_datetime, nowdate
from erpnext.projects.doctype.time_sheet.time_sheet import OverlapError
from erpnext.projects.doctype.time_sheet.time_sheet import make_salary_slip, make_sales_invoice

class TestTimeSheet(unittest.TestCase):
	def test_time_sheet_billing_amount(self):
		salary_structure = make_salary_structure("_T-Employee-0001")
		time_sheet = make_time_sheet("_T-Employee-0001", True)

		self.assertEquals(time_sheet.total_hours, 2)
		self.assertEquals(time_sheet.timesheets[0].billing_rate, 50)
		self.assertEquals(time_sheet.timesheets[0].billing_amount, 100)

	def test_salary_slip_from_timesheet(self):
		salary_structure = make_salary_structure("_T-Employee-0001")
		time_sheet = make_time_sheet("_T-Employee-0001", simulate = True)
		salary_slip = make_salary_slip(time_sheet.name)
		salary_slip.submit()

		self.assertEquals(salary_slip.total_working_hours, 2)
		self.assertEquals(salary_slip.hour_rate, 50)
		self.assertEquals(salary_slip.net_pay, 150)
		self.assertEquals(salary_slip.timesheets[0].time_sheet, time_sheet.name)
		self.assertEquals(salary_slip.timesheets[0].working_hours, 2)
		
		time_sheet = frappe.get_doc('Time Sheet', time_sheet.name)
		self.assertEquals(time_sheet.status, 'Payslip')
		salary_slip.cancel()

		time_sheet = frappe.get_doc('Time Sheet', time_sheet.name)
		self.assertEquals(time_sheet.status, 'Submitted')

	def test_sales_invoice_from_timesheet(self):
		time_sheet = make_time_sheet("_T-Employee-0001", simulate = True, billable = 1)
		sales_invoice = make_sales_invoice(time_sheet.name)
		sales_invoice.customer = "_Test Customer"
		sales_invoice.due_date = nowdate()

		item = sales_invoice.append('items', {})
		item.item_code = '_Test Item'
		item.qty = 2
		item.rate = 100

		sales_invoice.submit()
		
		time_sheet = frappe.get_doc('Time Sheet', time_sheet.name)
		self.assertEquals(sales_invoice.total_billing_amount, 100)
		self.assertEquals(time_sheet.status, 'Billed')

def make_salary_structure(employee):
	name = frappe.db.get_value('Salary Structure', {'employee': employee, 'salary_slip_based_on_timesheet': 1}, 'name')
	if name:
		frappe.delete_doc('Salary Structure', name)

	salary_structure = frappe.new_doc("Salary Structure")
	salary_structure.salary_slip_based_on_timesheet = 1
	salary_structure.employee = employee
	salary_structure.from_date = nowdate()
	salary_structure.earning_type = "Basic"
	salary_structure.hour_rate = 50.0
	salary_structure.company= "_Test Company"

	salary_structure.set('earnings', [])
	salary_structure.set('deductions', [])

	es = salary_structure.append('earnings', {
		"earning_type": "_Test Allowance",
		"modified_value": 100 
	})

	ds = salary_structure.append('deductions', {
		"deduction_type": "_Test Professional Tax",
		"d_modified_amt": 50
	})

	salary_structure.save(ignore_permissions=True)

	return salary_structure

def make_time_sheet(employee, simulate=False, billable = 0):
	update_activity_type("_Test Activity Type")
	time_sheet = frappe.new_doc("Time Sheet")
	time_sheet.employee = employee
	time_sheet_detail = time_sheet.append('timesheets', {})
	time_sheet_detail.billable = billable
	time_sheet_detail.activity_type = "_Test Activity Type"
	time_sheet_detail.from_time = now_datetime()
	time_sheet_detail.hours = 2
	time_sheet_detail.to_time = time_sheet_detail.from_time + datetime.timedelta(hours= time_sheet_detail.hours)

	for data in time_sheet.get('timesheets'):
		if simulate:
			while True:
				try:
					time_sheet.save()
					break
				except OverlapError:
					data.from_time = data.from_time + datetime.timedelta(minutes=10)
					data.to_time = data.from_time + datetime.timedelta(hours= data.hours)
		else:
			time_sheet.save()

	time_sheet.submit()

	return time_sheet

def update_activity_type(activity_type):
	activity_type = frappe.get_doc('Activity Type',activity_type)
	activity_type.billing_rate = 50.0
	activity_type.save(ignore_permissions=True)