# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.payroll.doctype.overtime_type.test_overtime_type import create_overtime_type
from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure
from erpnext.hr.doctype.shift_type.test_shift_type import create_shift_type
from erpnext.hr.doctype.employee_checkin.test_employee_checkin import make_checkin
from frappe.utils import today, add_days, get_datetime
from datetime import timedelta
import unittest


class TestOvertimeSlip(unittest.TestCase):
	def tearDown(self):
		for doctype in ["Overtime Type","Overtime Slip", "Attendance", "Employee Checkin", "Shift Type"]:
			frappe.db.sql("DELETE FROM `tab{0}`".format(doctype))

		frappe.db.sql("DELETE FROM `tabEmployee` WHERE user_id = 'test_employee@overtime.com'")
		frappe.db.commit()

	def test_overtime_based_on_attendance_without_shift_type(self):
		frappe.db.set_value("Payroll Settings", None, "overtime_based_on", "Attendance")
		frappe.db.set_value("Payroll Settings", None, "fetch_standard_working_hours_from_shift_type", 0)
		frappe.db.set_value("HR Settings", None, "standard_working_hours", 7)

		employee = make_employee("test_employee@overtime.com", company='_Test Company')
		make_salary_structure("structure for Overtime", "Monthly", employee=employee)
		overtime_type = create_overtime_type(employee=employee)
		attendance_record = create_attendance_records_for_overtime(employee, overtime_type.name)
		slip = create_overtime_slip(employee)

		for detail in slip.overtime_details:
			self.assertIn(detail.reference_document, attendance_record.keys())
			if detail.reference_document in attendance_record.keys():
				self.assertEqual(detail.overtime_duration, attendance_record[detail.reference_document]["overtime_duration"])
				self.assertEqual(str(detail.date), attendance_record[detail.reference_document]["attendance_date"])

	def test_overtime_based_on_attendance_with_shift_type_through_employee_checkins(self):
		frappe.db.set_value("Payroll Settings", None, "overtime_based_on", "Attendance")
		frappe.db.set_value("Payroll Settings", None, "fetch_standard_working_hours_from_shift_type", 1)

		shift_type = create_shift_type()
		shift_type.allow_overtime = 1
		shift_type.process_attendance_after = add_days(today(), -1)
		shift_type.last_sync_of_checkin = get_datetime(add_days(today(), 1))
		shift_type.save()

		print(shift_type.standard_working_time, shift_type.allow_overtime)

		employee = make_employee("test_employee@overtime.com", company='_Test Company')
		make_salary_structure("structure for Overtime", "Monthly", employee=employee)

		frappe.db.set_value("Employee", employee, "default_shift", shift_type.name)

		checkin = make_checkin(employee, time = get_datetime(today()) + timedelta(hours=9), log_type="IN")
		checkout = make_checkin(employee, time = get_datetime(today()) + timedelta(hours=20), log_type="OUT")

		print("Checkins Asserted")
		print(checkin.name)
		print(checkout.name)
		self.assertEqual(checkin.shift, shift_type.name)
		self.assertEqual(checkout.shift, shift_type.name)

		create_overtime_type(employee=employee)
		shift_type.reload()
		shift_type.process_auto_attendance()
		print(employee)


		checkin.reload()

		attendance_records = frappe.get_all("Attendance", filters = {
			'shift': shift_type.name, 'status': 'Present'
		}, fields = ["name", "overtime_duration", "overtime_type", "attendance_date"])

		from pprint import pprint
		pprint(attendance_records)

		records = {}
		for record in attendance_records:
			records[record.name] = {
				"overtime_duration": record.overtime_duration,
				"overtime_type": record.overtime_type,
				"attendance_date": record.attendance_date
			}

		slip = create_overtime_slip(employee)

		for detail in slip.overtime_details:
			self.assertIn(detail.reference_document, records.keys())
			if detail.reference_document in records.keys():
				self.assertEqual(detail.overtime_duration, records[detail.reference_document]["overtime_duration"])
				self.assertEqual(str(detail.date), str(records[detail.reference_document]["attendance_date"]))

	def test_overtime_based_on_timesheet(self):
		frappe.db.set_value("Payroll Settings", None, "overtime_based_on", "Timesheet")
		frappe.db.set_value("HR Settings", None, "standard_working_hours", 7)

		employee = make_employee("test_employee@overtime.com", company='_Test Company')
		make_salary_structure("structure for Overtime", "Monthly", employee=employee)
		overtime_type = create_overtime_type(employee=employee)
		time_log, timesheet = create_timesheet_record_for_overtime(employee, overtime_type.name)
		slip = create_overtime_slip(employee)

		for detail in slip.overtime_details:
			self.assertEqual(time_log.overtime_hours * 3600, detail.overtime_duration)
			self.assertEqual(time_log.overtime_on, get_datetime(detail.date))
			self.assertEqual(time_log.overtime_type, detail.overtime_type)
			self.assertEqual(timesheet, detail.reference_document)

def create_attendance_records_for_overtime(employee, overtime_type):
	records = {}
	for x in range(2):
		attendance = frappe.new_doc('Attendance')
		attendance.employee = employee
		attendance.status = 'Present'
		attendance.attendance_date = add_days(today(), -(x))
		attendance.overtime_type = overtime_type
		#for convertion to duration
		attendance.overtime_duration = 2 * 3600

		attendance.save()
		attendance.submit()

		records[attendance.name] = {
			"overtime_duration": attendance.overtime_duration,
			"overtime_type": attendance.overtime_type,
			"attendance_date": attendance.attendance_date
		}

	return records

def create_timesheet_record_for_overtime(employee, overtime_type):
	timesheet =frappe.new_doc("Timesheet")
	timesheet.employee = employee

	timesheet.time_logs = []
	time_log = {
		"activity_type": "Planning",
		"from_time": get_datetime(add_days(today(), -1)),
		"to_time": get_datetime(add_days(today(), 2)),
		"expected_hours": 48,
		"hours": 48,
		"is_overtime": 1,
		"overtime_type": overtime_type,
		"overtime_on": get_datetime(today()),
		"overtime_hours": 7
	}
	timesheet.append("time_logs", time_log)

	timesheet.save()
	timesheet.submit()

	return frappe._dict(time_log), timesheet.name


def create_overtime_slip(employee):
	slip = frappe.new_doc("Overtime Slip")
	slip.employee = employee

	slip.overtime_details = []

	slip.save()
	return slip

