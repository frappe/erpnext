// Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.require("assets/erpnext/js/financial_statements.js");

frappe.query_reports["Cash Flow"] = erpnext.financial_statements;
