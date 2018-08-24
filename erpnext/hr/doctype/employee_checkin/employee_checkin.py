# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import datetime, time
import frappe
from frappe.model.document import Document

class EmployeeCheckin(Document):
	def validate(self):
		if self.employee:
			attendance = frappe.db.get_list("Attendance",
				{"employee": self.employee,
				"attendance_date": datetime.datetime.now()},
				["name"]
			)
			if not attendance:
				employee_doc = frappe.get_doc("Employee", self.employee)
				## Create Employee Attendance
				employee_attendance = frappe.new_doc("Attendance")
				employee_attendance.company = employee_doc.company
				employee_attendance.employee = employee_doc.name
				employee_attendance.employee_name = employee_doc.employee_name
				employee_attendance.status = "Present"
				employee_attendance.attendance_date =  datetime.datetime.now()
				employee_attendance.department = employee_doc.department
				employee_attendance.save()
				employee_attendance.submit()

		if self.out_time:
			in_time = datetime.datetime(*time.strptime(str(self.in_time), "%Y-%m-%d %H:%M:%S")[:6])
			out_time = datetime.datetime(*time.strptime(str(self.out_time), "%Y-%m-%d %H:%M:%S")[:6])
			if in_time > out_time:
				frappe.throw("Out-time must be later than In-time.")
			else:
				duration = out_time - in_time
				self.duration = duration

@frappe.whitelist(allow_guest=False)
def punch_in(rfid_tag):
	if "Auto Attendance" in frappe.get_roles(frappe.session.user):
		employee = frappe.get_value('Employee', {'rfid_tag': rfid_tag}, "name")
		if employee:
			employee_doc = frappe.get_doc("Employee", employee)
			if employee_doc.status == 'Left':
				return employee_not_active(rfid_tag)
			else:
				if emp_checkin_exist(employee):
					return [{
						"status":"error",
						"error_message":"Already punched in."
					}]
				else:
					check_in = frappe.new_doc("Employee Checkin")
					check_in.company = employee_doc.company
					check_in.employee = employee
					check_in.employee_name = employee_doc.employee_name
					check_in.in_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
					check_in.save()
					return [{
						"status":"success",
						"employee_name":employee_doc.employee_name,
						"rfid_tag":employee_doc.rfid_tag,
						"in_time":check_in.in_time,
					}]
		else:
			return rfid_unknown(rfid_tag)
	else:
		return user_not_authorized()

@frappe.whitelist(allow_guest=False)
def punch_out(rfid_tag):
	if "Auto Attendance" in frappe.get_roles(frappe.session.user):
		employee = frappe.get_value('Employee', {'rfid_tag': rfid_tag}, "name")
		if employee:
			employee_doc = frappe.get_doc("Employee", employee)
			if employee_doc.status == 'Left':
				return employee_not_active(rfid_tag)
			else:

				if emp_checkin_exist(employee):
					checkout = frappe.db.sql("""Select name from `tabEmployee Checkin` where employee = %s and out_time is null""",(employee))
					checkout_rec = checkout[0][0]
					emp_check_doc = frappe.get_doc("Employee Checkin", (checkout_rec))
					emp_check_doc.out_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
					emp_check_doc.save()
					emp_check_doc.submit()
					return [{
						"status":"success",
						"employee_name":employee_doc.employee_name,
						"rfid_tag":employee_doc.rfid_tag,
						"in_time":emp_check_doc.in_time,
						"out_time":emp_check_doc.out_time,
						"duration":emp_check_doc.duration
					}]
				else:
					return [{
						"status":"error",
						"error_message":"Not punched in."
					}]
		else:
			return rfid_unknown(rfid_tag)
	else:
		return user_not_authorized()

def rfid_unknown(rfid_tag):
	return [{
		"status":"error",
		"error_message":"RFID Tag unknown."
	}]

def employee_not_active(rfid_tag):
	return [{
		"status":"error",
		"error_message":"Employee not active."
	}]

def emp_checkin_exist(employee):
	return frappe.db.sql("""Select name from `tabEmployee Checkin` where employee = %s and out_time is null""",(employee))

def user_not_authorized():
	return [{
		"status":"error",
		"error_message":"User not authorized."
	}]
