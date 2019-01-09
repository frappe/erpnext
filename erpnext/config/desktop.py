# coding=utf-8

from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "Item",
			"_doctype": "Item",
			"color": "#f39c12",
			"icon": "octicon octicon-package",
			"type": "link",
			"link": "List/Item"
		},
		{
			"module_name": "Customer",
			"_doctype": "Customer",
			"color": "#1abc9c",
			"icon": "octicon octicon-tag",
			"type": "link",
			"link": "List/Customer"
		},
		{
			"module_name": "Supplier",
			"_doctype": "Supplier",
			"color": "#c0392b",
			"icon": "octicon octicon-briefcase",
			"type": "link",
			"link": "List/Supplier"
		},
		{
			"_doctype": "Employee",
			"module_name": "Employee",
			"color": "#2ecc71",
			"icon": "octicon octicon-organization",
			"type": "link",
			"link": "List/Employee"
		},
		{
			"module_name": "Projects",
			"color": "#8e44ad",
			"icon": "octicon octicon-rocket",
			"type": "module",
		},
		{
			"module_name": "Issue",
			"color": "#2c3e50",
			"icon": "octicon octicon-issue-opened",
			"_doctype": "Issue",
			"type": "link",
			"link": "List/Issue"
		},
		{
			"module_name": "Lead",
			"icon": "octicon octicon-broadcast",
			"_doctype": "Lead",
			"type": "link",
			"link": "List/Lead"
		},
		{
			"module_name": "Profit and Loss Statement",
			"_doctype": "Account",
			"color": "#3498db",
			"icon": "octicon octicon-repo",
			"type": "link",
			"link": "query-report/Profit and Loss Statement"
		},

		# old
		{
			"label": _("Accounting"),
			"module_name": "Accounts",
			"color": "#3498db",
			"icon": "octicon octicon-repo",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "Stock",
			"color": "#f39c12",
			"icon": "octicon octicon-package",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "CRM",
			"color": "#EF4DB6",
			"icon": "octicon octicon-broadcast",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "Selling",
			"color": "#1abc9c",
			"icon": "octicon octicon-tag",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "Buying",
			"color": "#c0392b",
			"icon": "octicon octicon-briefcase",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "HR",
			"color": "#2ecc71",
			"icon": "octicon octicon-organization",
			"label": _("Human Resources"),
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "Manufacturing",
			"color": "#7f8c8d",
			"icon": "octicon octicon-tools",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "POS",
			"color": "#589494",
			"icon": "octicon octicon-credit-card",
			"type": "page",
			"link": "pos",
			"label": _("POS")
		},
		{
			"module_name": "Leaderboard",
			"color": "#589494",
			"icon": "octicon octicon-graph",
			"type": "page",
			"link": "leaderboard",
			"label": _("Leaderboard")
		},
		{
			"module_name": "Support",
			"color": "#2c3e50",
			"icon": "octicon octicon-issue-opened",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "Help",
			"color": "#FF888B",
			"icon": "octicon octicon-device-camera-video",
			"type": "module",
			"is_help": True,
			"label": _("Help"),
			"hidden": 1
		},
		{
			"module_name": "Maintenance",
			"color": "#FF888B",
			"icon": "octicon octicon-tools",
			"type": "module",
			"label": _("Maintenance"),
			"hidden": 1
		},
		{
			"module_name": "Student",
			"color": "#c0392b",
			"icon": "octicon octicon-person",
			"label": _("Student"),
			"link": "List/Student",
			"_doctype": "Student",
			"type": "list",
			"hidden": 1
		},
		{
			"module_name": "Student Group",
			"color": "#d59919",
			"icon": "octicon octicon-organization",
			"label": _("Student Group"),
			"link": "List/Student Group",
			"_doctype": "Student Group",
			"type": "list",
			"hidden": 1
		},
		{
			"module_name": "Course Schedule",
			"color": "#fd784f",
			"icon": "octicon octicon-calendar",
			"label": _("Course Schedule"),
			"link": "List/Course Schedule/Calendar",
			"_doctype": "Course Schedule",
			"type": "list",
			"hidden": 1
		},
		{
			"module_name": "Student Attendance Tool",
			"color": "#C0392B",
			"icon": "octicon octicon-checklist",
			"label": _("Student Attendance Tool"),
			"link": "List/Student Attendance Tool",
			"_doctype": "Student Attendance Tool",
			"type": "list",
			"hidden": 1
		},
		{
			"module_name": "Course",
			"color": "#8e44ad",
			"icon": "octicon octicon-book",
			"label": _("Course"),
			"link": "List/Course",
			"_doctype": "Course",
			"type": "list",
			"hidden": 1
		},
		{
			"module_name": "Program",
			"color": "#9b59b6",
			"icon": "octicon octicon-repo",
			"label": _("Program"),
			"link": "List/Program",
			"_doctype": "Program",
			"type": "list",
			"hidden": 1
		},
		{
			"module_name": "Student Applicant",
			"color": "#4d927f",
			"icon": "octicon octicon-clippy",
			"label": _("Student Applicant"),
			"link": "List/Student Applicant",
			"_doctype": "Student Applicant",
			"type": "list",
			"hidden": 1
		},
		{
			"module_name": "Fees",
			"color": "#83C21E",
			"icon": "fa fa-money",
			"label": _("Fees"),
			"link": "List/Fees",
			"_doctype": "Fees",
			"type": "list",
			"hidden": 1
		},
		{
			"module_name": "Instructor",
			"color": "#a99e4c",
			"icon": "octicon octicon-broadcast",
			"label": _("Instructor"),
			"link": "List/Instructor",
			"_doctype": "Instructor",
			"type": "list",
			"hidden": 1
		},
		{
			"module_name": "Room",
			"color": "#f22683",
			"icon": "fa fa-map-marker",
			"label": _("Room"),
			"link": "List/Room",
			"_doctype": "Room",
			"type": "list",
			"hidden": 1
		},
		{
			"module_name": "Education",
			"color": "#428B46",
			"icon": "octicon octicon-mortar-board",
			"type": "module",
			"label": _("Education"),
			"hidden": 1
		},
		{
			"module_name": "Healthcare",
			"color": "#FF888B",
			"icon": "fa fa-heartbeat",
			"type": "module",
			"label": _("Healthcare"),
			"hidden": 1
		},
        {
			"module_name": "Patient",
			"color": "#6BE273",
			"icon": "fa fa-user",
			"doctype": "Patient",
			"type": "link",
			"link": "List/Patient",
			"label": _("Patient"),
			"hidden": 1
        },
        {
			"module_name": "Healthcare Practitioner",
			"color": "#2ecc71",
			"icon": "fa fa-user-md",
			"doctype": "Healthcare Practitioner",
			"type": "link",
			"link": "List/Healthcare Practitioner",
			"label": _("Healthcare Practitioner"),
			"hidden": 1
        },
        {
			"module_name": "Patient Appointment",
			"color": "#934F92",
			"icon": "fa fa-calendar-plus-o",
			"doctype": "Patient Appointment",
			"type": "link",
			"link": "List/Patient Appointment",
			"label": _("Patient Appointment"),
			"hidden": 1
        },
        {
			"module_name": "Patient Encounter",
			"color": "#2ecc71",
			"icon": "fa fa-stethoscope",
			"doctype": "Patient Encounter",
			"type": "link",
			"link": "List/Patient Encounter",
			"label": _("Patient Encounter"),
			"hidden": 1
        },
        {
			"module_name": "Lab Test",
			"color": "#7578f6",
			"icon": "octicon octicon-beaker",
			"doctype": "Lab Test",
			"type": "list",
			"link": "List/Lab Test",
			"label": _("Lab Test"),
			"hidden": 1
        },
        {
			"module_name": "Vital Signs",
			"color": "#2ecc71",
			"icon": "fa fa-thermometer-empty",
			"doctype": "Vital Signs",
			"type": "list",
			"link": "List/Vital Signs",
			"label": _("Vital Signs"),
			"hidden": 1
        },
        {
			"module_name": "Clinical Procedure",
			"color": "#FF888B",
			"icon": "fa fa-medkit",
			"doctype": "Clinical Procedure",
			"type": "list",
			"link": "List/Clinical Procedure",
			"label": _("Clinical Procedure"),
			"hidden": 1
        },
        {
			"module_name": "Inpatient Record",
			"color": "#7578f6",
			"icon": "fa fa-list-alt",
			"doctype": "Inpatient Record",
			"type": "list",
			"link": "List/Inpatient Record",
			"label": _("Inpatient Record"),
			"hidden": 1
        },
		{
			"module_name": "Hub",
			"color": "#009248",
			"icon": "/assets/erpnext/images/hub_logo.svg",
			"type": "page",
			"link": "Hub/Item",
			"label": _("Hub")
		},
		{
			"module_name": "Data Import",
			"color": "#FFF168",
			"reverse": 1,
			"doctype": "Data Import",
			"icon": "octicon octicon-cloud-upload",
			"label": _("Data Import"),
			"link": "List/Data Import",
			"type": "list"
		},
		{
			"module_name": "Restaurant",
			"color": "#EA81E8",
			"icon": "🍔",
			"_doctype": "Restaurant",
			"type": "module",
			"link": "List/Restaurant",
			"label": _("Restaurant"),
			"hidden": 1
		},
		{
			"module_name": "Hotels",
			"color": "#EA81E8",
			"icon": "fa fa-bed",
			"type": "module",
			"label": _("Hotels"),
			"hidden": 1
		},
		{
			"module_name": "Agriculture",
			"color": "#8BC34A",
			"icon": "octicon octicon-globe",
			"type": "module",
			"label": _("Agriculture"),
			"hidden": 1
		},
		{
			"module_name": "Crop",
			"_doctype": "Crop",
			"label": _("Crop"),
			"color": "#8BC34A",
			"icon": "fa fa-tree",
			"type": "list",
			"link": "List/Crop",
			"hidden": 1
		},
		{
			"module_name": "Crop Cycle",
			"_doctype": "Crop Cycle",
			"label": _("Crop Cycle"),
			"color": "#8BC34A",
			"icon": "fa fa-circle-o-notch",
			"type": "list",
			"link": "List/Crop Cycle",
			"hidden": 1
		},
		{
			"module_name": "Fertilizer",
			"_doctype": "Fertilizer",
			"label": _("Fertilizer"),
			"color": "#8BC34A",
			"icon": "fa fa-leaf",
			"type": "list",
			"link": "List/Fertilizer",
			"hidden": 1
		},
		{
			"module_name": "Location",
			"_doctype": "Location",
			"label": _("Location"),
			"color": "#8BC34A",
			"icon": "fa fa-map",
			"type": "list",
			"link": "List/Location",
			"hidden": 1
		},
		{
			"module_name": "Disease",
			"_doctype": "Disease",
			"label": _("Disease"),
			"color": "#8BC34A",
			"icon": "octicon octicon-bug",
			"type": "list",
			"link": "List/Disease",
			"hidden": 1
		},
		{
			"module_name": "Plant Analysis",
			"_doctype": "Plant Analysis",
			"label": _("Plant Analysis"),
			"color": "#8BC34A",
			"icon": "fa fa-pagelines",
			"type": "list",
			"link": "List/Plant Analysis",
			"hidden": 1
		},
		{
			"module_name": "Soil Analysis",
			"_doctype": "Soil Analysis",
			"label": _("Soil Analysis"),
			"color": "#8BC34A",
			"icon": "fa fa-flask",
			"type": "list",
			"link": "List/Soil Analysis",
			"hidden": 1
		},
		{
			"module_name": "Soil Texture",
			"_doctype": "Soil Texture",
			"label": _("Soil Texture"),
			"color": "#8BC34A",
			"icon": "octicon octicon-beaker",
			"type": "list",
			"link": "List/Soil Texture",
			"hidden": 1
		},
		{
			"module_name": "Water Analysis",
			"_doctype": "Water Analysis",
			"label": _("Water Analysis"),
			"color": "#8BC34A",
			"icon": "fa fa-tint",
			"type": "list",
			"link": "List/Water Analysis",
			"hidden": 1
		},
		{
			"module_name": "Weather",
			"_doctype": "Weather",
			"label": _("Weather"),
			"color": "#8BC34A",
			"icon": "fa fa-sun-o",
			"type": "list",
			"link": "List/Weather",
			"hidden": 1
		},
		{
			"module_name": "Assets",
			"color": "#4286f4",
			"icon": "octicon octicon-database",
			"hidden": 1,
			"label": _("Assets"),
			"type": "module"
		},
		{
			"module_name": "Grant Application",
			"color": "#E9AB17",
			"icon": "fa fa-gift",
			"_doctype": "Grant Application",
			"type": "list",
			"link": "List/Grant Application",
			"label": _("Grant Application"),
			"hidden": 1

		},
		{
			"module_name": "Donor",
			"color": "#7F5A58",
			"icon": "fa fa-tint",
			"_doctype": "Donor",
			"type": "list",
			"link": "List/Donor",
			"label": _("Donor"),
			"hidden": 1
		},
		{
			"module_name": "Volunteer",
			"color": "#7E587E",
			"icon": "fa fa-angellist",
			"_doctype": "Volunteer",
			"type": "list",
			"link": "List/Volunteer",
			"label": _("Volunteer"),
			"hidden": 1
		},
		{
			"module_name": "Member",
			"color": "#79BAEC",
			"icon": "fa fa-users",
			"_doctype": "Member",
			"type": "list",
			"link": "List/Member",
			"label": _("Member"),
			"hidden": 1
		},
		{
			"module_name": "Chapter",
			"color": "#3B9C9C",
			"icon": "fa fa-handshake-o",
			"_doctype": "Chapter",
			"type": "list",
			"link": "List/Chapter",
			"label": _("Chapter"),
			"hidden": 1
		},
		{
			"module_name": "Non Profit",
			"color": "#DE2B37",
			"icon": "octicon octicon-heart",
			"type": "module",
			"label": _("Non Profit"),
			"hidden": 1
		},
		{
			"module_name": "Quality Management",
			"color": "blue",
			"icon": "octicon octicon-package",
			"type": "module",
			"label": _("Quality Management")
		}
	]
