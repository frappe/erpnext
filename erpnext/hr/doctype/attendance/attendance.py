# -*- coding: utf-8 -*-

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import getdate, nowdate
from frappe import _
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name
from frappe.utils import cint, getdate, formatdate, add_years
import pymssql
from datetime import tzinfo, timedelta, datetime
from dateutil import parser


class Attendance(Document):
			
	def validate_duplicate_record(self):
		res = frappe.db.sql("""select name from `tabAttendance` where employee = %s and attendance_date = %s
			and name != %s and docstatus = 1""",
			(self.employee, self.attendance_date, self.name))
		if res:
			frappe.throw(_("Attendance for employee {0} is already marked").format(self.employee))

		set_employee_name(self)

	def check_leave_record(self):
		leave_record = frappe.db.sql("""select leave_type, half_day from `tabLeave Application`
			where employee = %s and %s between from_date and to_date and status = 'Approved'
			and docstatus = 1""", (self.employee, self.attendance_date), as_dict=True)
		if leave_record:
			if leave_record[0].half_day:
				self.status = 'Half Day'
				frappe.msgprint(_("Employee {0} on Half day on {1}").format(self.employee, self.attendance_date))
			else:
				self.status = 'On Leave'
				self.leave_type = leave_record[0].leave_type
				frappe.msgprint(_("Employee {0} on Leave on {1}").format(self.employee, self.attendance_date))
		#~ if self.status == "On Leave" and not leave_record:
			#~ frappe.throw(_("No leave record found for employee {0} for {1}").format(self.employee, self.attendance_date))

	def validate_attendance_date(self):
		pass

	def validate_employee(self):
		emp = frappe.db.sql("select name from `tabEmployee` where name = %s and status = 'Active'",
		 	self.employee)
		if not emp:
			frappe.throw(_("Employee {0} is not active or does not exist").format(self.employee))

	def validate(self):
		from erpnext.controllers.status_updater import validate_status
		validate_status(self.status, ["Present", "Absent", "On Leave", "Half Day","Late","Early Leave"])
		self.validate_attendance_date()
		self.validate_duplicate_record()
		self.check_leave_record()


@frappe.whitelist(allow_guest=True)
def get_from_clock():
	import datetime
	from frappe.utils import get_datetime,getdate, cint, add_months, date_diff, add_days,today
	#~ at = frappe.get_list('Attendance', fields=["name"] )
	#~ for a in at :
		#~ frappe.delete_doc("Attendance", a.name)
	#~ return "s"
	
	conn = pymssql.connect(server="192.168.66.17",port=1433,user="hr",password="asd2013*",database="TR510")
	cursor = conn.cursor()
	#~ cursor.execute("""select TOP 30 * from Real_TR510_Data as mt where ID = %s  ORDER BY mt.Serial DESC""","0136")
	#~ cursor.execute("""select TOP 1000 * from Real_TR510_Data as mt  ORDER BY mt.Serial DESC""")
	#~ cursor.execute("""select TOP 1000 * from Real_TR510_Data as mt  ORDER BY mt.Serial DESC""")
	#~ cursor.execute("""select TOP 100 mt.Date from Real_TR510_Data as mt where mt.Date = cast(cast(getdate() as varchar(12)) as datetime) ORDER BY mt.Serial DESC""")
	cursor.execute("""select * from Real_TR510_Data as mt where mt.Date =dateadd(day,datediff(day,0,GETDATE()),0) ORDER BY mt.Serial DESC""")
	data = cursor.fetchall()
	def_att_h = frappe.db.get_single_value("HR Settings", "attendance_hours")
	if not data:
		return "No Data"
	for row in data:
		ah = frappe.get_doc("Attendance Hours",def_att_h)
		employee = frappe.get_list('Employee', fields=["name","attendance_hours"] , filters={"attendance_clock_number":int(row[2])})
		if employee:
			attendance_name=""
			if employee[0].attendance_hours:
				ah = frappe.get_doc("Attendance Hours",employee[0].attendance_hours)
				print "Emp H CHanged : ",employee[0].name,employee[0].attendance_hours
				
			start_time =get_datetime((datetime.datetime.min + ah.start_time)).time()
			start_allow_time =get_datetime((datetime.datetime.min + ah.allow_start_time)).time()
			end_time =get_datetime((datetime.datetime.min + ah.end_time)).time()
			end_allow_time =get_datetime((datetime.datetime.min + ah.allow_end_time)).time()
			
			attendance_list = frappe.db.sql( """select name from `tabAttendance` where employee = %s and attendance_date = %s""", (employee[0].name, row[0].date()))	
			if attendance_list:				
				attendance_name = attendance_list[0][0]
			else:
				try:
					attendance = frappe.new_doc("Attendance")
					#~ return formatdate(row[0])			
					attendance.attendance_date = row[0]
					attendance.employee = employee[0].name
					attendance.insert()
					attendance_name = attendance.name
					print ("Insert ",attendance_name)
				except:
					attendance_name="In Valid"
					print ("Bad Insert ",attendance_name)
			
			
			attendance_movement = frappe.get_list('Attendance Movement', fields=["name"] , filters={"serial":row[6],"parent":attendance_name})
			if attendance_movement:
				#~ print "E ",attendance_name ," ",ah.name," ",str(ah.start_time)
				p_doc = frappe.get_doc("Attendance",attendance_name)
				for am in attendance_movement:
					doc = frappe.get_doc("Attendance Movement",am.name)
					move_time = get_datetime(doc.time).time()	
					print "T "," ",str(start_allow_time)," ",str(end_allow_time)," ",str(move_time)	," ",str(doc.move_type)	," ",str(attendance_name)	
					if doc.move_type =="دخول" :
						if time_between_times(move_time,start_allow_time,end_allow_time):
							p_doc.status = "Late"		
							print "Late ",am.name +" ",ah.name		
					elif doc.move_type =="خروج":
						if time_between_times(move_time,start_allow_time,end_allow_time):
							p_doc.status = "Early Leave"
							print "Early Leave ",am.name,ah.name
					p_doc.save()
			else:
				doc = frappe.get_doc("Attendance",attendance_name)
				doc.attendance_date = row[0]
				child = doc.append('attendance_movement', {})	
				move_type ="Other"
				move_time = get_datetime(row[1]).time()
				if row[3] == 1 :
					move_type ="دخول"
					if time_between_times(move_time,start_allow_time,end_allow_time):
						doc.status = "Late"
				if row[3] == 2 :
					move_type ="خروج"
					if time_between_times(move_time,start_allow_time,end_allow_time):
						doc.status = "Early Leave"
				if row[3] == 3 :
					move_type ="رجوع من مهمة"
				if row[3] == 4 :
					move_type ="خروج لمهمة"
				
				
				child.serial = row[6]
				child.move_type = move_type
				child.time = row[1]
				child.mach_no = row[5]
				doc.save()


	return "data"
	
	
def time_between_times(move_time,start_time,end_time):
	if start_time == end_time :
		return True
	elif end_time < start_time : 
		return move_time <= end_time or move_time >= start_time
	else:
		return move_time <= end_time and move_time >= start_time

def validate_absence_and_notify():

	emps = frappe.get_list("Employee", filters = {"status": "Active"}, fields = ["name","employee_name"])
	super_emp_list = []
	supers =frappe.get_all('UserRole', fields = ["parent"], filters={'role' : 'HR Manager'})
	for s in supers:
		super_emp_list.append(s.parent)
	
	for emp in emps:
		ab = frappe.db.sql("""select count(name) from tabAttendance where employee = '{0}' and status = 'Absent' and attendance_date between '{1}' and '{2}'""".format(emp.name, add_years(nowdate(), -1), nowdate()))
		if ab[0][0] >= 28:
			# print ab[0][0]
			for s in super_emp_list:
				message = "This Employee {0}:{1} has {2} absence days during this year".format(emp.name, emp.employee_name, ab[0][0])
				notify({
					# for post in messages
					"message": message,
					"message_to": s,
					# for email
					"subject": "Employee Absence"
				})



def notify(args):
	args = frappe._dict(args)
	from frappe.desk.page.chat.chat import post
	post(**{"txt": args.message, "contact": args.message_to, "subject": args.subject,
	"notify": 1})

# cint(self.follow_via_email)