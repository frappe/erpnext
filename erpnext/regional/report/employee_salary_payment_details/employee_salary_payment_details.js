// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.require("assets/erpnext/js/salary_slip_deductions_report.js", function() {
	frappe.query_reports["Employee Salary Payment Details"] = erpnext.salary_slip_deductions_report;

	frappe.query_reports["Employee Salary Payment Details"]["filters"].push({
		"fieldname": "mode_of_payment",
		"label": __("Mode Of Payment"),
		"fieldtype": "Select",
		"options":[
			{ "value": "Bank", "label": __("Bank") },
			{ "value": "Cash", "label": __("Cash") },
			{ "value": "Cheque", "label": __("Cheque") },
			]
	});

});

