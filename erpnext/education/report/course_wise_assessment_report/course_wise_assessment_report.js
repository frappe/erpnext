// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Course wise Assessment Report"] = {
	"filters": [
		{
			"fieldname":"academic_year",
			"label": __("Academic Year"),
			"fieldtype": "Link",
			"options": "Academic Year",
			"reqd": 1
		},
		{
			"fieldname":"academic_term",
			"label": __("Academic Term"),
			"fieldtype": "Link",
			"options": "Academic Term"
		},
		{
			"fieldname":"course",
			"label": __("Course"),
			"fieldtype": "Link",
			"options": "Course",
			"reqd": 1
		},
		{
			"fieldname":"student_group",
			"label": __("Student Group"),
			"fieldtype": "Link",
			"options": "Student Group"
		},
		{
			"fieldname":"assessment_group",
			"label": __("Assessment Group"),
			"fieldtype": "Link",
			"options": "Assessment Group",
			"reqd": 1
		}
	]
};
