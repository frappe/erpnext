# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate
from erpnext.hr.doctype.employee_onboarding.employee_onboarding import make_employee
from erpnext.hr.doctype.employee_onboarding.employee_onboarding import IncompleteTaskError

class TestEmployeeOnboarding(unittest.TestCase):
	def test_employee_onboarding_incomplete_task(self):
		if frappe.db.exists('Employee Onboarding', {'employee_name': 'Test Applicant'}):
			return frappe.get_doc('Employee Onboarding', {'employee_name': 'Test Applicant'})
		_set_up()
		applicant = get_job_applicant()
		onboarding = frappe.new_doc('Employee Onboarding')
		onboarding.job_applicant = applicant.name
		onboarding.employee_name = 'Test Applicant'
		onboarding.company = '_Test Company'
		onboarding.designation = 'Researcher'
		onboarding.append('activities', {
			'activity_name': 'Assign ID Card',
			'role': 'HR User',
			'required_for_employee_creation': 1
		})
		onboarding.append('activities', {
			'activity_name': 'Assign a laptop',
			'role': 'HR User'
		})
		onboarding.status = 'Pending'
		onboarding.insert()
		onboarding.submit()
		self.assertEqual(onboarding.project, 'Employee Onboarding : Test Researcher - test@researcher.com')
		self.assertRaises(IncompleteTaskError, make_employee, onboarding.name)
		return onboarding

	def test_employee_onboarding_completed_task(self):
		doc = self.test_employee_onboarding_incomplete_task()
		project = frappe.get_doc('Project', doc.project)
		project.tasks[0].status = 'Closed'
		project.save()
		doc.reload()
		employee = make_employee(doc.name)
		employee.first_name = employee.employee_name
		employee.date_of_joining = nowdate()
		employee.date_of_birth = '1990-05-08'
		employee.gender = 'Female'
		employee.insert()
		self.assertEqual(employee.employee_name, 'Test Applicant')

def get_job_applicant():
	if frappe.db.exists('Job Applicant', 'Test Researcher - test@researcher.com'):
		return frappe.get_doc('Job Applicant', 'Test Researcher - test@researcher.com')
	applicant = frappe.new_doc('Job Applicant')
	applicant.applicant_name = 'Test Researcher'
	applicant.email_id = 'test@researcher.com'
	applicant.status = 'Open'
	applicant.cover_letter = 'I am a great Researcher.'
	applicant.insert()
	return applicant

def _set_up():
	for doctype in ["Employee Onboarding"]:
		frappe.db.sql("delete from `tab{doctype}`".format(doctype=doctype))