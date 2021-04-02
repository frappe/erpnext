from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql("""delete from tabDocPerm where role="Administrator" and parent in 
		("Payment Gateway", "Payment Gateway Account", "Payment Request", "Academic Term", "Academic Year", "Course",
		"Course Schedule", "Examination", "Fee Category", "Fee Structure", "Fees", "Instructor", "Program", "Program Enrollment Tool",
		"Room", "Scheduling Tool", "Student", "Student Applicant", "Student Attendance", "Student Group", "Student Group Creation Tool")
	""")