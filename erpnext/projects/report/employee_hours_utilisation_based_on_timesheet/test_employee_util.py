from __future__ import unicode_literals
import unittest
import frappe

from frappe.utils.make_random import get_random
from frappe.utils import get_timestamp
from erpnext.projects.report.employee_hours_utilisation_based_on_timesheet.employee_hours_utilisation_based_on_timesheet import execute
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.projects.doctype.project.test_project import make_project

class TestEmployeeUtilisation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create test employee
        cls.test_emp1 = make_employee("test@example.com", "_Test Company")
        cls.test_emp2 = make_employee("test1@example.com", "_Test Company")

        # Create test project
        cls.test_project = make_project({"project_name": "_Test Project"})

        # Create test timesheets
        cls.create_test_timesheets()

    @classmethod
    def create_test_timesheets(cls):
        timesheet1 = frappe.new_doc("Timesheet")
        timesheet1.employee = cls.test_emp1
        timesheet1.company = '_Test Company'

        timesheet1.append("time_logs", {
            "activity_type": get_random("Activity Type"),
            "hours": 5,
            "billable": 1,
            "from_time": '2021-04-01 13:30:00.000000',
            "to_time": '2021-04-01 18:30:00.000000'
        })

        timesheet1.save()
        timesheet1.submit()

        timesheet2 = frappe.new_doc("Timesheet")
        timesheet2.employee = cls.test_emp2
        timesheet2.company = '_Test Company'

        timesheet2.append("time_logs", {
            "activity_type": get_random("Activity Type"),
            "hours": 10,
            "billable": 0,
            "from_time": '2021-04-01 13:30:00.000000',
            "to_time": '2021-04-01 23:30:00.000000',
            "project": cls.test_project.name
        })

        timesheet2.save()
        timesheet2.submit()  

    @classmethod
    def tearDownClass(cls):
        # Delete time logs
        frappe.db.sql("""
            DELETE FROM `tabTimesheet Detail`
            WHERE parent IN (
                SELECT name 
                FROM `tabTimesheet` 
                WHERE company = '_Test Company'
            )
        """)

        frappe.db.sql("DELETE FROM `tabTimesheet` WHERE company='_Test Company'")
        frappe.db.sql(f"DELETE FROM `tabProject` WHERE name='{cls.test_project.name}'")

    def test_utilisation_report_with_required_filters_only(self):
        filters = {
            "company": "_Test Company",
            "from_date": "2021-04-01",
            "to_date": "2021-04-03" 
        }

        report = execute(filters)

        expected_data = [
            {
                'employee': 'EMP-00002', 
                'billed_hours': 0.0, 
                'non_billed_hours': 10.0, 
                'total_hours': 18.0, 
                'untracked_hours': 8.0, 
                'per_util': 55.56
            }, 
            {
                'employee': 'EMP-00001', 
                'billed_hours': 5.0, 
                'non_billed_hours': 0.0, 
                'total_hours': 18.0, 
                'untracked_hours': 13.0, 
                'per_util': 27.78
            }
        ]

        self.assertEqual(report[1], expected_data)
    
    def test_utilisation_report_for_single_employee(self):
        filters = {
            "company": "_Test Company",
            "from_date": "2021-04-01",
            "to_date": "2021-04-03",
            "employee": self.test_emp1
        }

        report = execute(filters)

        expected_data = [
            {
                'employee': 'EMP-00001', 
                'billed_hours': 5.0, 
                'non_billed_hours': 0.0, 
                'total_hours': 18.0, 
                'untracked_hours': 13.0, 
                'per_util': 27.78
            }
        ]

        self.assertEqual(report[1], expected_data)

    def test_utilisation_report_for_project(self):
        filters = {
            "company": "_Test Company",
            "from_date": "2021-04-01",
            "to_date": "2021-04-03",
            "project": self.test_project.name
        }

        report = execute(filters)

        expected_data = [
            {
                'employee': 'EMP-00002', 
                'billed_hours': 0.0, 
                'non_billed_hours': 10.0, 
                'total_hours': 18.0, 
                'untracked_hours': 8.0, 
                'per_util': 55.56
            }
        ]

        self.assertEqual(report[1], expected_data)

    def test_report_summary_data(self):
        filters = {
            "company": "_Test Company",
            "from_date": "2021-04-01",
            "to_date": "2021-04-03"
        }

        report = execute(filters)
        summary = report[4]
        expected_summary_values = ['41.67%', 5.0, 10.0, 21.0]

        self.assertEqual(len(summary), 4)

        for i in range(4):
            self.assertEqual(
                summary[i]['value'], expected_summary_values[i]
        )
