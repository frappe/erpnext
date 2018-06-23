// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Final Assessment Grades"] = {
	"filters": [
		{
			"fieldname":"academic_year",
			"label": __("Academic Year"),
			"fieldtype": "Link",
			"options": "Academic Year",
			"reqd": 1
		},
		{
			"fieldname":"student_group",
			"label": __("Student Group"),
			"fieldtype": "Link",
			"options": "Student Group",
			"reqd": 1,
			"get_query": function() {
				return{
					filters: {
						"group_based_on": "Batch",
						"academic_year": frappe.query_report_filters_by_name.academic_year.value
					}
				};
			}
		},
		{
			"fieldname":"assessment_group",
			"label": __("Assessment Group"),
			"fieldtype": "Link",
			"options": "Assessment Group",
			"reqd": 1
		}

	]
}
