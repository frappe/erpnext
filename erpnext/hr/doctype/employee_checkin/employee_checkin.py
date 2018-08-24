# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import datetime, time
import frappe
from frappe.model.document import Document

class EmployeeCheckin(Document):
	def validate(self):
		if self.out_time:
			in_time = datetime.datetime(*time.strptime(str(self.in_time), "%Y-%m-%d %H:%M:%S")[:6])
			out_time = datetime.datetime(*time.strptime(str(self.out_time), "%Y-%m-%d %H:%M:%S")[:6])
			if in_time > out_time:
				frappe.throw("Out-time must be later than In-time.")
			else:
				duration = out_time - in_time
				self.duration = duration

@frappe.whitelist()
def punch_in(rfid_tag):
	employee = frappe.get_value('Employee', {'rfid_tag': rfid_tag}, "name")
	if employee:
		employee_doc = frappe.get_doc("Employee", employee)
		if employee_doc.status == 'Left':
			return [{"status":"error", "error_message":"Employee not active."
					}]
		else:
			if (frappe.db.sql("""Select name from `tabEmployee Checkin` where
				employee = %s and out_time is null""",(employee))):
				return [{"status":"error", "error_message":"Already punched in."
						}]
			else:

				check_in = frappe.new_doc("Employee Checkin")
				check_in.company = employee_doc.company
				check_in.employee = employee
				check_in.employee_name = employee_doc.employee_name
				check_in.in_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
				check_in.save()
				return [{"status":"success",
						"employee_name":employee_doc.employee_name,
						"rfid_tag":employee_doc.rfid_tag,
						"in_time":check_in.in_time,
						}]
	else:
		return [{"status":"error", "error_message":"RFID tag unknown."
				}]

@frappe.whitelist()
def punch_out(rfid_tag):
	employee = frappe.get_value('Employee', {'rfid_tag': rfid_tag}, "name")
	if employee:
		employee_doc = frappe.get_doc("Employee", employee)
		if employee_doc.status == 'Left':
			return [{"status":"error", "error_message":"Employee not active."
					}]
		else:

			if frappe.db.sql("""Select name from `tabEmployee Checkin` where employee = %s and out_time is null""",(employee)):
				checkout = frappe.db.sql("""Select name from `tabEmployee Checkin` where employee = %s and out_time is null""",(employee))
				checkout_rec = checkout[0][0]
				emp_check_doc = frappe.get_doc("Employee Checkin", (checkout_rec))
				emp_check_doc.out_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
				emp_check_doc.save()
				emp_check_doc.submit()
				return [{"status":"success",
						"employee_name":employee_doc.employee_name,
						"rfid_tag":employee_doc.rfid_tag,
						"in_time":emp_check_doc.in_time,
						"out_time":emp_check_doc.out_time,
						"duration":emp_check_doc.duration
						}]
			else:
				return [{"status":"error", "error_message":"Not punched in."
				}]
	else:
		return [{"status":"error", "error_message":"RFID Tag unknown."
				}]
