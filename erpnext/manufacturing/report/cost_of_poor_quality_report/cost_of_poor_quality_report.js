// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Cost of Poor Quality Report"] = {
	"filters": [
		{
			label: __("Company"),
			fieldname: "company",
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			label: __("From Date"),
			fieldname:"from_date",
			fieldtype: "Datetime",
			default: frappe.datetime.convert_to_system_tz(frappe.datetime.add_months(frappe.datetime.now_datetime(), -1)),
			reqd: 1
		},
		{
			label: __("To Date"),
			fieldname:"to_date",
			fieldtype: "Datetime",
			default: frappe.datetime.now_datetime(),
			reqd: 1,
		},
		{
			label: __("Job Card"),
			fieldname: "name",
			fieldtype: "Link",
			options: "Job Card",
			get_query: function() {
				return {
					filters: {
						is_corrective_job_card: 1,
						docstatus: 1
					}
				}
			}
		},
		{
			label: __("Work Order"),
			fieldname: "work_order",
			fieldtype: "Link",
			options: "Work Order"
		},
		{
			label: __("Operation"),
			fieldname: "operation",
			fieldtype: "Link",
			options: "Operation",
			get_query: function() {
				return {
					filters: {
						is_corrective_operation: 1
					}
				}
			}
		},
		{
			label: __("Workstation"),
			fieldname: "workstation",
			fieldtype: "Link",
			options: "Workstation"
		},
		{
			label: __("Item"),
			fieldname: "production_item",
			fieldtype: "Link",
			options: "Item"
		},
		{
			label: __("Serial No"),
			fieldname: "serial_no",
			fieldtype: "Link",
			options: "Serial No",
			depends_on: "eval: doc.production_item",
			get_query: function() {
				var item_code = frappe.query_report.get_filter_value('production_item');
				return {
					filters: {
						item_code: item_code
					}
				}
			}
		},
		{
			label: __("Batch No"),
			fieldname: "batch_no",
			fieldtype: "Link",
			options: "Batch No",
			depends_on: "eval: doc.production_item",
			get_query: function() {
				var item_code = frappe.query_report.get_filter_value('production_item');
				return {
					filters: {
						item: item_code
					}
				}
			}
		},
	]
};
