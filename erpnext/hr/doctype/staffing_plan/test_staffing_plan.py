# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from frappe.utils import add_days, nowdate

from erpnext.hr.doctype.staffing_plan.staffing_plan import (
	ParentCompanyError,
	SubsidiaryCompanyError,
)

test_dependencies = ["Designation"]

class TestStaffingPlan(unittest.TestCase):
	def test_staffing_plan(self):
		_set_up()
		frappe.db.set_value("Company", "_Test Company 3", "is_group", 1)
		if frappe.db.exists("Staffing Plan", "Test"):
			return
		staffing_plan = frappe.new_doc("Staffing Plan")
		staffing_plan.company = "_Test Company 10"
		staffing_plan.name = "Test"
		staffing_plan.from_date = nowdate()
		staffing_plan.to_date = add_days(nowdate(), 10)
		staffing_plan.append("staffing_details", {
			"designation": "Designer",
			"vacancies": 6,
			"estimated_cost_per_position": 50000
		})
		staffing_plan.insert()
		staffing_plan.submit()
		self.assertEqual(staffing_plan.total_estimated_budget, 300000.00)

	def test_staffing_plan_subsidiary_company(self):
		self.test_staffing_plan()
		if frappe.db.exists("Staffing Plan", "Test 1"):
			return
		staffing_plan = frappe.new_doc("Staffing Plan")
		staffing_plan.company = "_Test Company 3"
		staffing_plan.name = "Test 1"
		staffing_plan.from_date = nowdate()
		staffing_plan.to_date = add_days(nowdate(), 10)
		staffing_plan.append("staffing_details", {
			"designation": "Designer",
			"vacancies": 3,
			"estimated_cost_per_position": 45000
		})
		self.assertRaises(SubsidiaryCompanyError, staffing_plan.insert)

	def test_staffing_plan_parent_company(self):
		_set_up()
		if frappe.db.exists("Staffing Plan", "Test"):
			return
		staffing_plan = frappe.new_doc("Staffing Plan")
		staffing_plan.company = "_Test Company 3"
		staffing_plan.name = "Test"
		staffing_plan.from_date = nowdate()
		staffing_plan.to_date = add_days(nowdate(), 10)
		staffing_plan.append("staffing_details", {
			"designation": "Designer",
			"vacancies": 7,
			"estimated_cost_per_position": 50000
		})
		staffing_plan.insert()
		staffing_plan.submit()
		self.assertEqual(staffing_plan.total_estimated_budget, 350000.00)
		if frappe.db.exists("Staffing Plan", "Test 1"):
			return
		staffing_plan = frappe.new_doc("Staffing Plan")
		staffing_plan.company = "_Test Company 10"
		staffing_plan.name = "Test 1"
		staffing_plan.from_date = nowdate()
		staffing_plan.to_date = add_days(nowdate(), 10)
		staffing_plan.append("staffing_details", {
			"designation": "Designer",
			"vacancies": 7,
			"estimated_cost_per_position": 60000
		})
		staffing_plan.insert()
		self.assertRaises(ParentCompanyError, staffing_plan.submit)

def _set_up():
	for doctype in ["Staffing Plan", "Staffing Plan Detail"]:
		frappe.db.sql("delete from `tab{doctype}`".format(doctype=doctype))
	make_company()

def make_company():
	if frappe.db.exists("Company", "_Test Company 10"):
		return

	company = frappe.new_doc("Company")
	company.company_name = "_Test Company 10"
	company.abbr = "_TC10"
	company.parent_company = "_Test Company 3"
	company.default_currency = "INR"
	company.country = "Pakistan"
	company.insert()
