# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
import unittest

class TestOvertimeType(unittest.TestCase):
	pass

def create_overtime_type(**args):
	args = frappe._dict(args)

	overtime_type = frappe.new_doc("Overtime Type")
	overtime_type.name = "Test Overtime"
	overtime_type.applicable_for = args.applicable_for or "Employee"
	if overtime_type.applicable_for == "Department":
		overtime_type.department = args.department
	elif overtime_type.applicable_for == "Employee Grade":
		overtime_type.employee_grade = args.employee_grade
	else:
		overtime_type.employee = args.employee

	overtime_type.standard_multiplier = 1.25
	overtime_type.applicable_for_weekend =  args.applicable_for_weekend or 0
	overtime_type.applicable_for_public_holiday =  args.applicable_for_public_holiday or 0

	if args.applicable_for_weekend:
		overtime_type.weekend_multiplier = 1.5

	if args.applicable_for_public_holidays:
		overtime_type.public_holiday_multiplier = 2

	overtime_type.append("applicable_salary_component", {
		"salary_component": "Basic Salary"
	})

	overtime_type.save()

	return overtime_type



