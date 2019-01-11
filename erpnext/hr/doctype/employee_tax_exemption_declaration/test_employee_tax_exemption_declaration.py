# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe, erpnext
import unittest
from erpnext.hr.doctype.employee.test_employee import make_employee

class TestEmployeeTaxExemptionDeclaration(unittest.TestCase):
	def setUp(self):
		make_employee("employee@taxexepmtion.com")
		make_employee("employee1@taxexepmtion.com")
		create_payroll_period()
		create_exemption_category()
		frappe.db.sql("""delete from `tabEmployee Tax Exemption Declaration`""")

	def test_exemption_amount_greater_than_category_max(self):
		declaration = frappe.get_doc({
			"doctype": "Employee Tax Exemption Declaration",
			"employee": frappe.get_value("Employee", {"user_id":"employee@taxexepmtion.com"}, "name"),
			"payroll_period": "_Test Payroll Period",
			"declarations": [dict(exemption_sub_category = "_Test Sub Category",
							exemption_category = "_Test Category",
							amount = 150000)]
		})
		self.assertRaises(frappe.ValidationError, declaration.save)
		declaration = frappe.get_doc({
			"doctype": "Employee Tax Exemption Declaration",
			"payroll_period": "_Test Payroll Period",
			"employee": frappe.get_value("Employee", {"user_id":"employee@taxexepmtion.com"}, "name"),
			"declarations": [dict(exemption_sub_category = "_Test Sub Category",
							exemption_category = "_Test Category",
							amount = 90000)]
		})
		self.assertTrue(declaration.save)

	def test_duplicate_category_in_declaration(self):
		declaration = frappe.get_doc({
			"doctype": "Employee Tax Exemption Declaration",
			"employee": frappe.get_value("Employee", {"user_id":"employee@taxexepmtion.com"}, "name"),
			"company": "_Test Company",
			"payroll_period": "_Test Payroll Period",
			"declarations": [dict(exemption_sub_category = "_Test Sub Category",
							exemption_category = "_Test Category",
							amount = 100000),
							dict(exemption_sub_category = "_Test Sub Category",
							exemption_category = "_Test Category",
							amount = 50000),
							]
		})
		self.assertRaises(frappe.ValidationError, declaration.save)

	def test_duplicate_submission_for_payroll_period(self):
		declaration = frappe.get_doc({
			"doctype": "Employee Tax Exemption Declaration",
			"employee": frappe.get_value("Employee", {"user_id":"employee@taxexepmtion.com"}, "name"),
			"company": "_Test Company",
			"payroll_period": "_Test Payroll Period",
			"declarations": [dict(exemption_sub_category = "_Test Sub Category",
							exemption_category = "_Test Category",
							amount = 100000),
							dict(exemption_sub_category = "_Test1 Sub Category",
							exemption_category = "_Test Category",
							amount = 50000),
							]
		}).insert()
		declaration.submit()
		self.assertEquals(declaration.docstatus, 1)
		duplicate_declaration = frappe.get_doc({
			"doctype": "Employee Tax Exemption Declaration",
			"employee": frappe.get_value("Employee", {"user_id":"employee@taxexepmtion.com"}, "name"),
			"company":  "_Test Company",
			"payroll_period": "_Test Payroll Period",
			"declarations": [dict(exemption_sub_category = "_Test Sub Category",
							exemption_category = "_Test Category",
							amount = 100000)
							]
		}).insert()
		self.assertRaises(frappe.DocstatusTransitionError, duplicate_declaration.submit)
		duplicate_declaration.employee = frappe.get_value("Employee", {"user_id":"employee1@taxexepmtion.com"}, "name")
		self.assertTrue(duplicate_declaration.submit)

def create_payroll_period():
	if not frappe.db.exists("Payroll Period", "_Test Payroll Period"):
		from datetime import date
		payroll_period = frappe.get_doc(dict(
			doctype = 'Payroll Period',
			name = "_Test Payroll Period",
			company =  "_Test Company",
			start_date = date(date.today().year, 1, 1),
			end_date = date(date.today().year, 12, 31)
		)).insert()
		return payroll_period
	else:
		return frappe.get_doc("Payroll Period", "_Test Payroll Period")

def create_exemption_category():
	if not frappe.db.exists("Employee Tax Exemption Category", "_Test Category"):
		category = frappe.get_doc({
			"doctype": "Employee Tax Exemption Category",
			"name": "_Test Category",
			"deduction_component": "Income Tax",
			"max_amount": 100000
		}).insert()
	if not frappe.db.exists("Employee Tax Exemption Sub Category", "_Test Sub Category"):
		frappe.get_doc({
			"doctype": "Employee Tax Exemption Sub Category",
			"name": "_Test Sub Category",
			"exemption_category": "_Test Category",
			"max_amount": 100000,
			"is_active": 1
		}).insert()
	if not frappe.db.exists("Employee Tax Exemption Sub Category", "_Test1 Sub Category"):
		frappe.get_doc({
			"doctype": "Employee Tax Exemption Sub Category",
			"name": "_Test1 Sub Category",
			"exemption_category": "_Test Category",
			"max_amount": 50000,
			"is_active": 1
		}).insert()
