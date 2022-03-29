import unittest

import frappe
from frappe.utils.make_random import get_random

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.projects.doctype.project.test_project import make_project
from erpnext.projects.report.employee_hours_utilization_based_on_timesheet.employee_hours_utilization_based_on_timesheet import (
	execute,
)


class TestEmployeeUtilization(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		# Create test employee
		cls.test_emp1 = make_employee("test1@employeeutil.com", "_Test Company")
		cls.test_emp2 = make_employee("test2@employeeutil.com", "_Test Company")

		# Create test project
		cls.test_project = make_project({"project_name": "_Test Project"})

		# Create test timesheets
		cls.create_test_timesheets()

		frappe.db.set_value("HR Settings", "HR Settings", "standard_working_hours", 9)

	@classmethod
	def create_test_timesheets(cls):
		timesheet1 = frappe.new_doc("Timesheet")
		timesheet1.employee = cls.test_emp1
		timesheet1.company = "_Test Company"

		timesheet1.append(
			"time_logs",
			{
				"activity_type": get_random("Activity Type"),
				"hours": 5,
				"is_billable": 1,
				"from_time": "2021-04-01 13:30:00.000000",
				"to_time": "2021-04-01 18:30:00.000000",
			},
		)

		timesheet1.save()
		timesheet1.submit()

		timesheet2 = frappe.new_doc("Timesheet")
		timesheet2.employee = cls.test_emp2
		timesheet2.company = "_Test Company"

		timesheet2.append(
			"time_logs",
			{
				"activity_type": get_random("Activity Type"),
				"hours": 10,
				"is_billable": 0,
				"from_time": "2021-04-01 13:30:00.000000",
				"to_time": "2021-04-01 23:30:00.000000",
				"project": cls.test_project.name,
			},
		)

		timesheet2.save()
		timesheet2.submit()

	@classmethod
	def tearDownClass(cls):
		# Delete time logs
		frappe.db.sql(
			"""
            DELETE FROM `tabTimesheet Detail`
            WHERE parent IN (
                SELECT name
                FROM `tabTimesheet`
                WHERE company = '_Test Company'
            )
        """
		)

		frappe.db.sql("DELETE FROM `tabTimesheet` WHERE company='_Test Company'")
		frappe.db.sql(f"DELETE FROM `tabProject` WHERE name='{cls.test_project.name}'")

	def test_utilization_report_with_required_filters_only(self):
		filters = {"company": "_Test Company", "from_date": "2021-04-01", "to_date": "2021-04-03"}

		report = execute(filters)

		expected_data = self.get_expected_data_for_test_employees()
		self.assertEqual(report[1], expected_data)

	def test_utilization_report_for_single_employee(self):
		filters = {
			"company": "_Test Company",
			"from_date": "2021-04-01",
			"to_date": "2021-04-03",
			"employee": self.test_emp1,
		}

		report = execute(filters)

		emp1_data = frappe.get_doc("Employee", self.test_emp1)
		expected_data = [
			{
				"employee": self.test_emp1,
				"employee_name": "test1@employeeutil.com",
				"billed_hours": 5.0,
				"non_billed_hours": 0.0,
				"department": emp1_data.department,
				"total_hours": 18.0,
				"untracked_hours": 13.0,
				"per_util": 27.78,
				"per_util_billed_only": 27.78,
			}
		]

		self.assertEqual(report[1], expected_data)

	def test_utilization_report_for_project(self):
		filters = {
			"company": "_Test Company",
			"from_date": "2021-04-01",
			"to_date": "2021-04-03",
			"project": self.test_project.name,
		}

		report = execute(filters)

		emp2_data = frappe.get_doc("Employee", self.test_emp2)
		expected_data = [
			{
				"employee": self.test_emp2,
				"employee_name": "test2@employeeutil.com",
				"billed_hours": 0.0,
				"non_billed_hours": 10.0,
				"department": emp2_data.department,
				"total_hours": 18.0,
				"untracked_hours": 8.0,
				"per_util": 55.56,
				"per_util_billed_only": 0.0,
			}
		]

		self.assertEqual(report[1], expected_data)

	def test_utilization_report_for_department(self):
		emp1_data = frappe.get_doc("Employee", self.test_emp1)
		filters = {
			"company": "_Test Company",
			"from_date": "2021-04-01",
			"to_date": "2021-04-03",
			"department": emp1_data.department,
		}

		report = execute(filters)

		expected_data = self.get_expected_data_for_test_employees()
		self.assertEqual(report[1], expected_data)

	def test_report_summary_data(self):
		filters = {"company": "_Test Company", "from_date": "2021-04-01", "to_date": "2021-04-03"}

		report = execute(filters)
		summary = report[4]
		expected_summary_values = ["41.67%", "13.89%", 5.0, 10.0]

		self.assertEqual(len(summary), 4)

		for i in range(4):
			self.assertEqual(summary[i]["value"], expected_summary_values[i])

	def get_expected_data_for_test_employees(self):
		emp1_data = frappe.get_doc("Employee", self.test_emp1)
		emp2_data = frappe.get_doc("Employee", self.test_emp2)

		return [
			{
				"employee": self.test_emp2,
				"employee_name": "test2@employeeutil.com",
				"billed_hours": 0.0,
				"non_billed_hours": 10.0,
				"department": emp2_data.department,
				"total_hours": 18.0,
				"untracked_hours": 8.0,
				"per_util": 55.56,
				"per_util_billed_only": 0.0,
			},
			{
				"employee": self.test_emp1,
				"employee_name": "test1@employeeutil.com",
				"billed_hours": 5.0,
				"non_billed_hours": 0.0,
				"department": emp1_data.department,
				"total_hours": 18.0,
				"untracked_hours": 13.0,
				"per_util": 27.78,
				"per_util_billed_only": 27.78,
			},
		]
