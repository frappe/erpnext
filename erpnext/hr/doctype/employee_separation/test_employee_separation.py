# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from frappe.utils import getdate

test_dependencies = ['Employee Onboarding']

class TestEmployeeSeparation(unittest.TestCase):
	def test_employee_separation(self):
		separation = create_employee_separation()

		self.assertEqual(separation.docstatus, 1)
		self.assertEqual(separation.boarding_status, 'Pending')

		project = frappe.get_doc('Project', separation.project)
		project.percent_complete_method = 'Manual'
		project.status = 'Completed'
		project.save()

		separation.reload()
		self.assertEqual(separation.boarding_status, 'Completed')

		separation.cancel()
		self.assertEqual(separation.project, '')

	def tearDown(self):
		for entry in frappe.get_all('Employee Separation'):
			doc = frappe.get_doc('Employee Separation', entry.name)
			if doc.docstatus == 1:
				doc.cancel()
			doc.delete()

def create_employee_separation():
	employee = frappe.db.get_value('Employee', {'status': 'Active', 'company': '_Test Company'})
	separation = frappe.new_doc('Employee Separation')
	separation.employee = employee
	separation.boarding_begins_on = getdate()
	separation.company = '_Test Company'
	separation.append('activities', {
		'activity_name': 'Deactivate Employee',
		'role': 'HR User'
	})
	separation.boarding_status = 'Pending'
	separation.insert()
	separation.submit()
	return separation
