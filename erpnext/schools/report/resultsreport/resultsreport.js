// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["ResultsReport"] = {
	"filters": [
		{
			"fieldname":"student",
			"label": __("Student"),
			"fieldtype": "Link",
			"options": "Student",
			change: function() {
				var student = frappe.query_report_filters_by_name.student.get_value();
				if (!student){
					frappe.query_report_filters_by_name.student_name.set_value("");
					return false;
				}
				frappe.db.get_value("Student", student, "title", function(value) {
					frappe.query_report_filters_by_name.student_name.set_value(value["title"]);
				});
			}
		},
		{
			"fieldname":"academic_year",
			"label": __("Academic Year"),
			"fieldtype": "Link",
			"options": "Academic Year"
		},
		{
			"fieldname":"student_name",
			"label": __("Party Name"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"academic_term",
			"label": __("Academic Term"),
			"fieldtype": "Link",
			"options": "Academic Term"
		}

	]
}
