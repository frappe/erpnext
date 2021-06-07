// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.query_reports["COGS By Item Group"] = {
	filters: [
    {
      label: __("Company"),
      fieldname: "company",
      fieldtype: "Link",
      options: "Company",
      mandatory: true,
			default: frappe.defaults.get_user_default("Company"),
    },
    // {
      // label: __("Account"),
      // fieldname: "account",
      // fieldtype: "Link",
      // options: "Account",
      // mandatory: true,
			// get_query() {
				// const company = frappe.query_report.get_filter_value('company');
				// return {
					// "doctype": "Account",
					// "filters": {
						// "company": company,
					// }
				// }
			// },
    // },
    {
      label: __("From Date"),
      fieldname: "from_date",
      fieldtype: "Date",
      mandatory: true,
      default: frappe.datetime.year_start(),
    },
    {
      label: __("To Date"),
      fieldname: "to_date",
      fieldtype: "Date",
      mandatory: true,
      default: frappe.datetime.get_today(),
    },
	]
};
