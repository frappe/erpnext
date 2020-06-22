// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.require("assets/erpnext/js/salary_slip_deductions_report_filters.js", function() {

	let ecs_checklist_filter = erpnext.salary_slip_deductions_report_filters
	ecs_checklist_filter['filters'].push({
		fieldname: "type",
		label: __("Type"),
		fieldtype: "Select",
		options:["", "Bank", "Cash", "Cheque"]
	})

	frappe.query_reports["Salary Payments via ECS"] = ecs_checklist_filter
});
