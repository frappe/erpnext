# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}

	if not filters.get("date"):
		msgprint(_("Please select date"), raise_exception=1)
	
	columns = get_columns(filters)
	date = filters.get("date")

	absent_students = get_absent_students(date)
	leave_applicants = get_leave_applications(date)
	if absent_students:
		student_list = [d["student"] for d in absent_students]
		transportation_details = get_transportation_details(date, student_list)

	data = []
	for student in absent_students:
		if not student.student in leave_applicants:
			row = [student.student, student.student_name, student.student_group]
			stud_details = frappe.db.get_value("Student", student.student, ['student_email_id', 'student_mobile_number'], as_dict=True)
			
			if stud_details.student_email_id:
				row+=[stud_details.student_email_id]
			else:
				row+= [""]
			
			if stud_details.student_mobile_number:
				row+=[stud_details.student_mobile_number]
			else:
				row+= [""]
			if transportation_details.get(student.student):
				row += transportation_details.get(student.student)
				
			data.append(row)
	
	return columns, data

def get_columns(filters):
	columns = [ 
		_("Student") + ":Link/Student:90", 
		_("Student Name") + "::150", 
		_("Student Group") + "::180",
		_("Student Email Address") + "::180",
		_("Student Mobile No.") + "::150",
		_("Mode of Transportation") + "::150",
		_("Vehicle/Bus Number") + "::150",
	]
	return columns

def get_absent_students(date):
	absent_students = frappe.db.sql("""select student, student_name, student_group from `tabStudent Attendance` 
		where status="Absent" and date = %s order by student_group, student_name""", date, as_dict=1)
	return absent_students

def get_leave_applications(date):
	leave_applicants = []
	for student in frappe.db.sql("""select student from `tabStudent Leave Application` 
	where docstatus = 1 and from_date <= %s and to_date >= %s""", (date, date)):
		leave_applicants.append(student[0])
	return leave_applicants

def get_transportation_details(date, student_list):
	academic_year = frappe.get_all("Academic Year", filters=[["year_start_date", "<=", date],["year_end_date", ">=", date]])
	if academic_year:
		academic_year = academic_year[0].name
	elif frappe.defaults.get_defaults().academic_year:
		academic_year = frappe.defaults.get_defaults().academic_year
	else:
		return {}

	transportation_details = frappe.get_all("Program Enrollment", fields=["student", "mode_of_transportation", "vehicle_no"],
		filters={"student": ("in", student_list), "academic_year": academic_year, "docstatus": ("not in", ["2"])})
	transportation_map = {}
	for d in transportation_details:
		transportation_map[d.student] = [d.mode_of_transportation, d.vehicle_no]
	return transportation_map
