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
					"name": "Guardian"
				},
				{
					"type": "doctype",
					"name": "Student Log"
				},
				{
					"type": "doctype",
					"name": "Student Group"
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
					"name": "Web Academy Applicant"
				},
				{
					"type": "doctype",
					"name": "Student Admission"
				},
				{
					"type": "doctype",
					"name": "Program Enrollment"
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
			]
		},
		{
			"label": _("Tools"),
			"items": [
				{
					"type": "doctype",
					"name": "Student Attendance Tool"
				},
				{
					"type": "doctype",
					"name": "Assessment Result Tool"
				},
				{
					"type": "doctype",
					"name": "Student Group Creation Tool"
				},
				{
					"type": "doctype",
					"name": "Program Enrollment Tool"
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
					"name": "Assessment Plan"
				},
				{
					"type": "doctype",
					"name": "Assessment Group",
					"link": "Tree/Assessment Group",
				},
				{
					"type": "doctype",
					"name": "Assessment Result"
				},
				{
					"type": "doctype",
					"name": "Assessment Criteria"
				}
			]
		},
		{
			"label": _("Assessment Reports"),
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Course wise Assessment Report",
					"doctype": "Assessment Result"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Final Assessment Grades",
					"doctype": "Assessment Result"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Assessment Plan Status",
					"doctype": "Assessment Plan"
				},
				{
					"type": "doctype",
					"name": "Student Report Generation Tool"
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
					"name": "Fee Schedule"
				},
				{
					"type": "doctype",
					"name": "Fee Structure"
				},
				{
					"type": "doctype",
					"name": "Fee Category"
				}
			]
		},
		{
			"label": _("Schedule"),
			"items": [
				{
					"type": "doctype",
					"name": "Course Schedule",
					"route": "List/Course Schedule/Calendar"
				},
				{
					"type": "doctype",
					"name": "Course Scheduling Tool"
				}
			]
		},
		{
			"label": _("Masters"),
			"items": [
				{
					"type": "doctype",
					"name": "Program"
				},
				{
					"type": "doctype",
					"name": "Course"
				},
				{
					"type": "doctype",
					"name": "Article"
				},
				{
					"type": "doctype",
					"name": "Video"
				},
				{
					"type": "doctype",
					"name": "Quiz"
				},
				{
					"type": "doctype",
					"name": "Room"
				}
			]
		},
		{
			"label": _("LMS Activity"),
			"items": [
				{
					"type": "doctype",
					"name": "Course Enrollment"
				},
				{
					"type": "doctype",
					"name": "Course Activity"
				},
				{
					"type": "doctype",
					"name": "Quiz Activity"
				}
			]
		},
		{
			"label": _("Settings"),
			"items": [
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
					"name": "Grading Scale"
				},
				{
					"type": "doctype",
					"name": "Academic Term"
				},
				{
					"type": "doctype",
					"name": "Academic Year"
				},
				{
					"type": "doctype",
					"name": "Education Settings"
				}
			]
		},
		{
			"label": _("Other Reports"),
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Student and Guardian Contact Details",
					"doctype": "Program Enrollment"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Student Monthly Attendance Sheet",
					"doctype": "Student Attendance"
				},
				{
					"type": "report",
					"name": "Student Fee Collection",
					"doctype": "Fees",
					"is_query_report": True
				}
			]
		}
	]
