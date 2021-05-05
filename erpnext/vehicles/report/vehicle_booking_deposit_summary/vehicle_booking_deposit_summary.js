// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Vehicle Booking Deposit Summary"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today()
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today()
		},
		{
			fieldname: "deposit_type",
			label: __("Deposit Type"),
			fieldtype: "Select",
			options: "\nNCS\nDirect Deposit"
		},
		{
			fieldname: "from_allocation_period",
			label: __("From Allocation Period"),
			fieldtype: "Link",
			options: "Vehicle Allocation Period",
			on_change: function () {
				var period = frappe.query_report.get_filter_value('from_allocation_period');
				if (period) {
					frappe.query_report.set_filter_value('to_allocation_period', period);
				}
			}
		},
		{
			fieldname: "to_allocation_period",
			label: __("To Allocation Period"),
			fieldtype: "Link",
			options: "Vehicle Allocation Period"
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier"
		},
	]
};
