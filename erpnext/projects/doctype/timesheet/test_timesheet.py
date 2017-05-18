# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
import datetime
from frappe.utils.make_random import get_random
from frappe.utils import now_datetime, nowdate, add_days, add_months
from erpnext.projects.doctype.timesheet.timesheet import OverlapError
from erpnext.projects.doctype.timesheet.timesheet import make_salary_slip, make_sales_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

class TestTimesheet(unittest.TestCase):
	def test_timesheet_billing_amount(self):
		salary_structure = make_salary_structure("_T-Employee-0001")
		timesheet = make_timesheet("_T-Employee-0001", simulate = True, billable=1)

		self.assertEquals(timesheet.total_hours, 2)
		self.assertEquals(timesheet.total_billable_hours, 2)
		self.assertEquals(timesheet.time_logs[0].billing_rate, 50)
		self.assertEquals(timesheet.time_logs[0].billing_amount, 100)
		self.assertEquals(timesheet.total_billable_amount, 100)

	def test_salary_slip_from_timesheet(self):
		salary_structure = make_salary_structure("_T-Employee-0001")
		timesheet = make_timesheet("_T-Employee-0001", simulate = True, billable=1)
		salary_slip = make_salary_slip(timesheet.name)
		salary_slip.submit()

		self.assertEquals(salary_slip.total_working_hours, 2)
		self.assertEquals(salary_slip.hour_rate, 50)
		self.assertEquals(salary_slip.net_pay, 150)
		self.assertEquals(salary_slip.timesheets[0].time_sheet, timesheet.name)
		self.assertEquals(salary_slip.timesheets[0].working_hours, 2)
		
		timesheet = frappe.get_doc('Timesheet', timesheet.name)
		self.assertEquals(timesheet.status, 'Payslip')
		salary_slip.cancel()

		timesheet = frappe.get_doc('Timesheet', timesheet.name)
		self.assertEquals(timesheet.status, 'Submitted')

	def test_sales_invoice_from_timesheet(self):
		timesheet = make_timesheet("_T-Employee-0001", simulate = True, billable = 1)
		sales_invoice = make_sales_invoice(timesheet.name)
		sales_invoice.customer = "_Test Customer"
		sales_invoice.due_date = nowdate()

		item = sales_invoice.append('items', {})
		item.item_code = '_Test Item'
		item.qty = 2
		item.rate = 100

		sales_invoice.submit()
		timesheet = frappe.get_doc('Timesheet', timesheet.name)
		self.assertEquals(sales_invoice.total_billing_amount, 100)
		self.assertEquals(timesheet.status, 'Billed')

	def test_timesheet_billing_based_on_project(self):
		timesheet = make_timesheet("_T-Employee-0001", simulate=True, billable=1, project = '_Test Project', company='_Test Company')
		sales_invoice = create_sales_invoice(do_not_save=True)
		sales_invoice.project = '_Test Project'
		sales_invoice.submit()

		ts = frappe.get_doc('Timesheet', timesheet.name)
		self.assertEquals(ts.per_billed, 100)
		self.assertEquals(ts.time_logs[0].sales_invoice, sales_invoice.name)

def make_salary_structure(employee):
	name = frappe.db.get_value('Salary Structure Employee', {'employee': employee}, 'parent')
	if name:
		salary_structure = frappe.get_doc('Salary Structure', name)
	else:
		salary_structure = frappe.new_doc("Salary Structure")
		salary_structure.name = "Timesheet Salary Structure Test"
		salary_structure.salary_slip_based_on_timesheet = 1
		salary_structure.from_date = add_days(nowdate(), -30)
		salary_structure.salary_component = "Basic"
		salary_structure.hour_rate = 50.0
		salary_structure.company = "_Test Company"
		salary_structure.payment_account = get_random("Account")

		salary_structure.set('employees', [])
		salary_structure.set('earnings', [])
		salary_structure.set('deductions', [])

		es = salary_structure.append('employees', {
			"employee": employee,
			"base": 1200,
			"from_date": add_months(nowdate(),-1)
		})
		
		
		es = salary_structure.append('earnings', {
			"salary_component": "_Test Allowance",
			"amount": 100 
		})

		ds = salary_structure.append('deductions', {
			"salary_component": "_Test Professional Tax",
			"amount": 50
		})

		salary_structure.save(ignore_permissions=True)

	return salary_structure

def make_timesheet(employee, simulate=False, billable = 0, activity_type="_Test Activity Type", project=None, task=None, company=None):
	update_activity_type(activity_type)
	timesheet = frappe.new_doc("Timesheet")
	timesheet.employee = employee
	timesheet_detail = timesheet.append('time_logs', {})
	timesheet_detail.billable = billable
	timesheet_detail.activity_type = activity_type
	timesheet_detail.from_time = now_datetime()
	timesheet_detail.hours = 2
	timesheet_detail.to_time = timesheet_detail.from_time + datetime.timedelta(hours= timesheet_detail.hours)
	timesheet_detail.project = project
	timesheet_detail.task = task
	timesheet_detail.company = company or '_Test Company'

	for data in timesheet.get('time_logs'):
		if simulate:
			while True:
				try:
					timesheet.save(ignore_permissions=True)
					break
				except OverlapError:
					data.from_time = data.from_time + datetime.timedelta(minutes=10)
					data.to_time = data.from_time + datetime.timedelta(hours= data.hours)
		else:
			timesheet.save(ignore_permissions=True)

	timesheet.submit()

	return timesheet

def update_activity_type(activity_type):
	activity_type = frappe.get_doc('Activity Type',activity_type)
	activity_type.billing_rate = 50.0
	activity_type.save(ignore_permissions=True)
