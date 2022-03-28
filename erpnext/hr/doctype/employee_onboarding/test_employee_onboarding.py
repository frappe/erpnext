# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, getdate

from erpnext.hr.doctype.employee_onboarding.employee_onboarding import (
	IncompleteTaskError,
	make_employee,
)
from erpnext.hr.doctype.job_offer.test_job_offer import create_job_offer
from erpnext.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list


class TestEmployeeOnboarding(unittest.TestCase):
	def setUp(self):
		if frappe.db.exists("Employee Onboarding", {"employee_name": "Test Researcher"}):
			frappe.delete_doc("Employee Onboarding", {"employee_name": "Test Researcher"})

		project = "Employee Onboarding : test@researcher.com"
		frappe.db.sql("delete from tabProject where name=%s", project)
		frappe.db.sql("delete from tabTask where project=%s", project)

	def test_employee_onboarding_incomplete_task(self):
		onboarding = create_employee_onboarding()

		project_name = frappe.db.get_value("Project", onboarding.project, "project_name")
		self.assertEqual(project_name, "Employee Onboarding : test@researcher.com")

		# don't allow making employee if onboarding is not complete
		self.assertRaises(IncompleteTaskError, make_employee, onboarding.name)

		# boarding status
		self.assertEqual(onboarding.boarding_status, "Pending")

		# start and end dates
		start_date, end_date = frappe.db.get_value(
			"Task", onboarding.activities[0].task, ["exp_start_date", "exp_end_date"]
		)
		self.assertEqual(getdate(start_date), getdate(onboarding.boarding_begins_on))
		self.assertEqual(getdate(end_date), add_days(start_date, onboarding.activities[0].duration))

		start_date, end_date = frappe.db.get_value(
			"Task", onboarding.activities[1].task, ["exp_start_date", "exp_end_date"]
		)
		self.assertEqual(
			getdate(start_date), add_days(onboarding.boarding_begins_on, onboarding.activities[0].duration)
		)
		self.assertEqual(getdate(end_date), add_days(start_date, onboarding.activities[1].duration))

		# complete the task
		project = frappe.get_doc("Project", onboarding.project)
		for task in frappe.get_all("Task", dict(project=project.name)):
			task = frappe.get_doc("Task", task.name)
			task.status = "Completed"
			task.save()

		# boarding status
		onboarding.reload()
		self.assertEqual(onboarding.boarding_status, "Completed")

		# make employee
		onboarding.reload()
		employee = make_employee(onboarding.name)
		employee.first_name = employee.employee_name
		employee.date_of_joining = getdate()
		employee.date_of_birth = "1990-05-08"
		employee.gender = "Female"
		employee.insert()
		self.assertEqual(employee.employee_name, "Test Researcher")

	def tearDown(self):
		frappe.db.rollback()


def get_job_applicant():
	if frappe.db.exists("Job Applicant", "test@researcher.com"):
		return frappe.get_doc("Job Applicant", "test@researcher.com")
	applicant = frappe.new_doc("Job Applicant")
	applicant.applicant_name = "Test Researcher"
	applicant.email_id = "test@researcher.com"
	applicant.designation = "Researcher"
	applicant.status = "Open"
	applicant.cover_letter = "I am a great Researcher."
	applicant.insert()
	return applicant


def get_job_offer(applicant_name):
	job_offer = frappe.db.exists("Job Offer", {"job_applicant": applicant_name})
	if job_offer:
		return frappe.get_doc("Job Offer", job_offer)

	job_offer = create_job_offer(job_applicant=applicant_name)
	job_offer.submit()
	return job_offer


def create_employee_onboarding():
	applicant = get_job_applicant()
	job_offer = get_job_offer(applicant.name)

	holiday_list = make_holiday_list("_Test Employee Boarding")
	holiday_list = frappe.get_doc("Holiday List", holiday_list)
	holiday_list.holidays = []
	holiday_list.save()

	onboarding = frappe.new_doc("Employee Onboarding")
	onboarding.job_applicant = applicant.name
	onboarding.job_offer = job_offer.name
	onboarding.date_of_joining = onboarding.boarding_begins_on = getdate()
	onboarding.company = "_Test Company"
	onboarding.holiday_list = holiday_list.name
	onboarding.designation = "Researcher"
	onboarding.append(
		"activities",
		{
			"activity_name": "Assign ID Card",
			"role": "HR User",
			"required_for_employee_creation": 1,
			"begin_on": 0,
			"duration": 1,
		},
	)
	onboarding.append(
		"activities",
		{"activity_name": "Assign a laptop", "role": "HR User", "begin_on": 1, "duration": 1},
	)
	onboarding.status = "Pending"
	onboarding.insert()
	onboarding.submit()

	return onboarding
