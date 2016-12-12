from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Student"),
			"items": [

				{
					"type": "doctype",
					"name": "Student"
				},
				{
					"type": "doctype",
					"name": "Student Log"
				},
				{
					"type": "doctype",
					"name": "Student Batch"
				},
				{
					"type": "doctype",
					"name": "Student Group"
				},
				{
					"type": "doctype",
					"name": "Student Group Creation Tool"
				}
			]
		},
		{
			"label": _("Admission"),
			"items": [

				{
					"type": "doctype",
					"name": "Student Applicant"
				},
				{
					"type": "doctype",
					"name": "Student Admission"
				},
				{
					"type": "doctype",
					"name": "Program Enrollment"
				},
				{
					"type": "doctype",
					"name": "Program Enrollment Tool"
				},
				{
					"type": "doctype",
					"name": "Student Batch Creation Tool"
				}
			]
		},
		{
			"label": _("Attendance"),
			"items": [
				{
					"type": "doctype",
					"name": "Student Attendance"
				},
				{
					"type": "doctype",
					"name": "Student Leave Application"
				},
				{
					"type": "doctype",
					"name": "Student Attendance Tool"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Absent Student Report",
					"doctype": "Student Attendance"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Student Batch-Wise Attendance",
					"doctype": "Student Attendance"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Student Monthly Attendance Sheet",
					"doctype": "Student Attendance"
				}
			]
		},
		{
			"label": _("Schedule"),
			"items": [
				{
					"type": "doctype",
					"name": "Course Schedule",
					"route": "Calendar/Course Schedule"
				},
				{
					"type": "doctype",
					"name": "Course Scheduling Tool"
				}
			]
		},
		{
			"label": _("Assessment"),
			"items": [
				{
					"type": "doctype",
					"name": "Assessment"
				},
				{
					"type": "doctype",
					"name": "Assessment Group"
				},
				{
					"type": "doctype",
					"name": "Grading Structure"
				}
			]
		},
		{
			"label": _("Fees"),
			"items": [
				{
					"type": "doctype",
					"name": "Fees"
				},
				{
					"type": "doctype",
					"name": "Fee Structure"
				},
				{
					"type": "doctype",
					"name": "Fee Category"
				},
				{
					"type": "report",
					"name": "Student Fee Collection",
					"doctype": "Fees",
					"is_query_report": True
				}
			]
		},
		{
			"label": _("LMS"),
			"items": [
				{
					"type": "doctype",
					"name": "Announcement"
				},
				{
					"type": "doctype",
					"name": "Topic"
				},
				{
					"type": "doctype",
					"name": "Discussion"
				}
			]
		},
		{
			"label": _("Setup"),
			"items": [
				{
					"type": "doctype",
					"name": "Course"
				},
				{
					"type": "doctype",
					"name": "Program"
				},
				{
					"type": "doctype",
					"name": "Instructor"
				},
				{
					"type": "doctype",
					"name": "Room"
				},
				{
					"type": "doctype",
					"name": "Student Category"
				},
				{
					"type": "doctype",
					"name": "Student Batch Name"
				},
				{
					"type": "doctype",
					"name": "Academic Term"
				},
				{
					"type": "doctype",
					"name": "Academic Year"
				}
			]
		},
	]
