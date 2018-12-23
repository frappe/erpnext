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
from erpnext.accounting.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.hr.doctype.salary_structure.test_salary_structure \
	import make_salary_structure, create_salary_structure_assignment


class TestTimesheet(unittest.TestCase):
	def setUp(self):
		for dt in ["Salary Slip", "Salary Structure", "Salary Structure Assignment", "Timesheet"]:
			frappe.db.sql("delete from `tab%s`" % dt)

		if not frappe.db.exists("Salary Component", "Timesheet Component"):
			frappe.get_doc({"doctype": "Salary Component", "salary_component": "Timesheet Component"}).insert()


	def test_timesheet_billing_amount(self):
		make_salary_structure_for_timesheet("_T-Employee-00001")
		timesheet = make_timesheet("_T-Employee-00001", simulate=True, billable=1)

		self.assertEqual(timesheet.total_hours, 2)
		self.assertEqual(timesheet.total_billable_hours, 2)
		self.assertEqual(timesheet.time_logs[0].billing_rate, 50)
		self.assertEqual(timesheet.time_logs[0].billing_amount, 100)
		self.assertEqual(timesheet.total_billable_amount, 100)

	def test_timesheet_billing_amount_not_billable(self):
		make_salary_structure_for_timesheet("_T-Employee-00001")
		timesheet = make_timesheet("_T-Employee-00001", simulate=True, billable=0)

		self.assertEqual(timesheet.total_hours, 2)
		self.assertEqual(timesheet.total_billable_hours, 0)
		self.assertEqual(timesheet.time_logs[0].billing_rate, 0)
		self.assertEqual(timesheet.time_logs[0].billing_amount, 0)
		self.assertEqual(timesheet.total_billable_amount, 0)

	def test_salary_slip_from_timesheet(self):
		salary_structure = make_salary_structure_for_timesheet("_T-Employee-00001")
		timesheet = make_timesheet("_T-Employee-00001", simulate = True, billable=1)
		salary_slip = make_salary_slip(timesheet.name)
		salary_slip.submit()

		self.assertEqual(salary_slip.total_working_hours, 2)
		self.assertEqual(salary_slip.hour_rate, 50)
		self.assertEqual(salary_slip.earnings[0].salary_component, "Timesheet Component")
		self.assertEqual(salary_slip.earnings[0].amount, 100)
		self.assertEqual(salary_slip.timesheets[0].time_sheet, timesheet.name)
		self.assertEqual(salary_slip.timesheets[0].working_hours, 2)

		timesheet = frappe.get_doc('Timesheet', timesheet.name)
		self.assertEqual(timesheet.status, 'Payslip')
		salary_slip.cancel()

		timesheet = frappe.get_doc('Timesheet', timesheet.name)
		self.assertEqual(timesheet.status, 'Submitted')

	def test_sales_invoice_from_timesheet(self):
		timesheet = make_timesheet("_T-Employee-00001", simulate=True, billable=1)
		sales_invoice = make_sales_invoice(timesheet.name, '_Test Item', '_Test Customer')
		sales_invoice.due_date = nowdate()
		sales_invoice.submit()
		timesheet = frappe.get_doc('Timesheet', timesheet.name)
		self.assertEqual(sales_invoice.total_billing_amount, 100)
		self.assertEqual(timesheet.status, 'Billed')
		self.assertEqual(sales_invoice.customer, '_Test Customer')

		item = sales_invoice.items[0]
		self.assertEqual(item.item_code, '_Test Item')
		self.assertEqual(item.qty, 2.00)
		self.assertEqual(item.rate, 50.00)

	def test_timesheet_billing_based_on_project(self):
		timesheet = make_timesheet("_T-Employee-00001", simulate=True, billable=1, project = '_Test Project', company='_Test Company')
		sales_invoice = create_sales_invoice(do_not_save=True)
		sales_invoice.project = '_Test Project'
		sales_invoice.submit()

		ts = frappe.get_doc('Timesheet', timesheet.name)
		self.assertEqual(ts.per_billed, 100)
		self.assertEqual(ts.time_logs[0].sales_invoice, sales_invoice.name)

	def test_timesheet_time_overlap(self):
		settings = frappe.get_single('Projects Settings')
		initial_setting = settings.ignore_employee_time_overlap
		settings.ignore_employee_time_overlap = 0
		settings.save()

		update_activity_type("_Test Activity Type")
		timesheet = frappe.new_doc("Timesheet")
		timesheet.employee = "_T-Employee-00001"
		timesheet.append(
			'time_logs',
			{
				"billable": 1,
				"activity_type": "_Test Activity Type",
				"from_type": now_datetime(),
				"hours": 3,
				"company": "_Test Company"
			}
		)
		timesheet.append(
			'time_logs',
			{
				"billable": 1,
				"activity_type": "_Test Activity Type",
				"from_type": now_datetime(),
				"hours": 3,
				"company": "_Test Company"
			}
		)

		self.assertRaises(frappe.ValidationError, timesheet.save)

		settings.ignore_employee_time_overlap = 1
		settings.save()
		timesheet.save()  # should not throw an error

		settings.ignore_employee_time_overlap = initial_setting
		settings.save()

	def test_timesheet_std_working_hours(self):
		company = frappe.get_doc('Company', "_Test Company")
		company.standard_working_hours = 8
		company.save()

		timesheet = frappe.new_doc("Timesheet")
		timesheet.employee = "_T-Employee-00001"
		timesheet.company = '_Test Company'
		timesheet.append(
			'time_logs',
			{
				"activity_type": "_Test Activity Type",
				"from_time": now_datetime(),
				"to_time": now_datetime() + datetime.timedelta(days= 4)
			}
		)
		timesheet.save()

		ts = frappe.get_doc('Timesheet', timesheet.name)
		self.assertEqual(ts.total_hours, 32)
		ts.submit()
		ts.cancel()

		company = frappe.get_doc('Company', "_Test Company")
		company.standard_working_hours = 0
		company.save()

		timesheet = frappe.new_doc("Timesheet")
		timesheet.employee = "_T-Employee-00001"
		timesheet.company = '_Test Company'
		timesheet.append(
			'time_logs',
			{
				"activity_type": "_Test Activity Type",
				"from_time": now_datetime(),
				"to_time": now_datetime() + datetime.timedelta(days= 4)
			}
		)
		timesheet.save()

		ts = frappe.get_doc('Timesheet', timesheet.name)
		self.assertEqual(ts.total_hours, 96)
		ts.submit()
		ts.cancel()

def make_salary_structure_for_timesheet(employee):
	salary_structure_name = "Timesheet Salary Structure Test"
	frequency = "Monthly"

	salary_structure = make_salary_structure(salary_structure_name, frequency, dont_submit=True)
	salary_structure.salary_component = "Timesheet Component"
	salary_structure.salary_slip_based_on_timesheet = 1
	salary_structure.hour_rate = 50.0
	salary_structure.save()
	salary_structure.submit()

	if not frappe.db.get_value("Salary Structure Assignment",
		{'employee':employee, 'docstatus': 1}):
			create_salary_structure_assignment(employee, salary_structure.name)

	return salary_structure


def make_timesheet(employee, simulate=False, billable = 0, activity_type="_Test Activity Type", project=None, task=None, company=None):
	update_activity_type(activity_type)
	timesheet = frappe.new_doc("Timesheet")
	timesheet.employee = employee
	timesheet.company = company or '_Test Company'
	timesheet_detail = timesheet.append('time_logs', {})
	timesheet_detail.billable = billable
	timesheet_detail.activity_type = activity_type
	timesheet_detail.from_time = now_datetime()
	timesheet_detail.hours = 2
	timesheet_detail.to_time = timesheet_detail.from_time + datetime.timedelta(hours= timesheet_detail.hours)
	timesheet_detail.project = project
	timesheet_detail.task = task

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
