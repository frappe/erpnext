// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.require("assets/erpnext/js/salary_slip_deductions_report.js", function() {
	frappe.query_reports["Total Payments Based On Payment Mode"] = erpnext.salary_slip_deductions_report;
});