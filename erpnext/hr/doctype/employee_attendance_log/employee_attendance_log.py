# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import now
from frappe.model.document import Document
from frappe import _

class EmployeeAttendanceLog(Document):
	def validate(self):
		if frappe.db.exists('Employee Attendance Log', {'employee': self.employee, 'time': self.time}):
			frappe.throw(_('This log already exists for this employee.'))


@frappe.whitelist()
def add_log_based_on_biometric_rf_id(biometric_rf_id, timestamp, device_id=None, log_type=None):
	"""Finds the relevant Employee using the biometric_rf_id and creates a Employee Attendance Log.

	:param biometric_rf_id: The Biometric/RF tag ID as set up in Employee DocType.
	:param timestamp: The timestamp of the Log. Currently expected in the following format as string: '2019-05-08 10:48:08.000000'
	:param device_id: (optional)Location / Device ID. A short string is expected.
	:param log_type: (optional)Direction of the Punch if available (IN/OUT).
	"""

	if not biometric_rf_id or not timestamp:
		frappe.throw(_("'biometric_rf_id' and 'timestamp' are required."))

	employee = frappe.db.get_values("Employee", {"biometric_rf_id": biometric_rf_id}, ["name", "employee_name", "biometric_rf_id"], as_dict=True)
	if employee:
		employee = employee[0]
	else:
		frappe.throw(_("No Employee found for the given 'biometric_rf_id':{}.").format(biometric_rf_id))

	doc = frappe.new_doc("Employee Attendance Log")
	doc.employee = employee.name
	doc.employee_name = employee.employee_name
	doc.time = timestamp
	doc.device_id = device_id
	doc.log_type = log_type
	doc.insert()
	frappe.db.commit()
	
	return doc


def mark_attendance_and_link_log(logs, attendance_status, attendance_date, working_hours=None, company=None):
	"""Creates an attendance and links the attendance to the Employee Attendance Log.
	Note: If attendance is already present for the given date, the logs are marked as skipped and no exception is thrown.

	:param logs: The List of 'Employee Attendance Log'.
	:param attendance_status: Attendance status to be marked. One of: (Present, Absent, Half Day, Skip). Note: 'On Leave' is not supported by this function.
	:param attendance_date: Date of the attendance to be created.
	:param working_hours: (optional)Number of working hours for the given date.
	"""
	log_names = [x.name for x in logs]
	employee = logs[0].employee
	if attendance_status == 'Skip':
		frappe.db.sql("""update `tabEmployee Attendance Log`
			set skip_auto_attendance = %s
			where name in %s""", ('1', log_names))
		return None
	elif attendance_status in ('Present', 'Absent', 'Half Day'):
		employee_doc = frappe.get_doc('Employee', employee)
		if not frappe.db.exists('Attendance', {'employee':employee, 'attendance_date':attendance_date}):
			doc_dict = {
				'doctype': 'Attendance',
				'employee': employee,
				'attendance_date': attendance_date,
				'status': attendance_status,
				'working_hours': working_hours,
				'company': employee_doc.company
			}
			attendance = frappe.get_doc(doc_dict).insert()
			attendance.submit()
			frappe.db.sql("""update `tabEmployee Attendance Log`
				set attendance = %s
				where name in %s""", (attendance.name, log_names))
			return attendance
		else:
			frappe.db.sql("""update `tabEmployee Attendance Log`
				set skip_auto_attendance = %s
				where name in %s""", ('1', log_names))
			return None
	else:
		frappe.throw(_('{} is an invalid Attendance Status.').format(attendance_status))
