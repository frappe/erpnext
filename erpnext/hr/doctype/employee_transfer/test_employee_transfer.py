# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from datetime import date

import frappe
from frappe.utils import add_days, getdate

from erpnext.hr.doctype.employee.test_employee import make_employee


class TestEmployeeTransfer(unittest.TestCase):
	def setUp(self):
		make_employee("employee2@transfers.com")
		make_employee("employee3@transfers.com")
		create_company()
		create_employee()
		create_employee_transfer()

	def tearDown(self):
		frappe.db.rollback()

	def test_submit_before_transfer_date(self):
		transfer_obj = frappe.get_doc({
			"doctype": "Employee Transfer",
			"employee": frappe.get_value("Employee", {"user_id":"employee2@transfers.com"}, "name"),
			"transfer_details" :[
				{
				"property": "Designation",
				"current": "Software Developer",
				"new": "Project Manager",
				"fieldname": "designation"
				}
			]
		})
		transfer_obj.transfer_date = add_days(getdate(), 1)
		transfer_obj.save()
		self.assertRaises(frappe.DocstatusTransitionError, transfer_obj.submit)
		transfer = frappe.get_doc("Employee Transfer", transfer_obj.name)
		transfer.transfer_date = getdate()
		transfer.submit()
		self.assertEqual(transfer.docstatus, 1)

	def test_new_employee_creation(self):
		transfer = frappe.get_doc({
			"doctype": "Employee Transfer",
			"employee": frappe.get_value("Employee", {"user_id":"employee3@transfers.com"}, "name"),
			"create_new_employee_id": 1,
			"transfer_date": getdate(),
			"transfer_details" :[
				{
				"property": "Designation",
				"current": "Software Developer",
				"new": "Project Manager",
				"fieldname": "designation"
				}
			]
		}).insert()
		transfer.submit()
		self.assertTrue(transfer.new_employee_id)
		self.assertEqual(frappe.get_value("Employee", transfer.new_employee_id, "status"), "Active")
		self.assertEqual(frappe.get_value("Employee", transfer.employee, "status"), "Left")

	def test_employee_history(self):
		name = frappe.get_value("Employee", {"first_name": "John", "company": "Test Company"}, "name")
		doc = frappe.get_doc("Employee",name)
		count = 0
		department = ["Accounts - TC", "Management - TC"]
		designation = ["Accountant", "Manager"]
		dt = [getdate("01-10-2021"), date.today()]

		for data in doc.internal_work_history:
			self.assertEqual(data.department, department[count])
			self.assertEqual(data.designation, designation[count])
			self.assertEqual(data.from_date, dt[count])
			count = count + 1

		data = frappe.db.get_list("Employee Transfer", filters={"employee":name}, fields=["*"])
		doc = frappe.get_doc("Employee Transfer", data[0]["name"])
		doc.cancel()
		employee_doc = frappe.get_doc("Employee",name)

		for data in employee_doc.internal_work_history:
			self.assertEqual(data.designation, designation[0])
			self.assertEqual(data.department, department[0])
			self.assertEqual(data.from_date, dt[0])

def create_employee():
	doc = frappe.get_doc({
			"doctype": "Employee",
			"first_name": "John",
			"company": "Test Company",
			"gender": "Male",
			"date_of_birth": getdate("30-09-1980"),
			"date_of_joining": getdate("01-10-2021"),
			"department": "Accounts - TC",
			"designation": "Accountant"
	})

	doc.save()

def create_company():
	exists = frappe.db.exists("Company", "Test Company")
	if not exists:
		doc = frappe.get_doc({
				"doctype": "Company",
				"company_name": "Test Company",
				"default_currency": "INR",
				"country": "India"
		})

		doc.save()

def create_employee_transfer():
	doc = frappe.get_doc({
		"doctype": "Employee Transfer",
		"employee": frappe.get_value("Employee", {"first_name": "John", "company": "Test Company"}, "name"),
		"transfer_date": date.today(),
		"transfer_details": [
			{
				"property": "Designation",
				"current": "Accountant",
				"new": "Manager",
				"fieldname": "designation"
			},
			{
				"property": "Department",
				"current": "Accounts - TC",
				"new": "Management - TC",
				"fieldname": "department"
			}
		]
	})

	doc.save()
	doc.submit()