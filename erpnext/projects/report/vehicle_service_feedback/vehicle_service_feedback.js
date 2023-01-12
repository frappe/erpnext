// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Vehicle Service Feedback"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "date_type",
			label: __("Date Type"),
			fieldtype: "Select",
			options: ["Feedback Due Date", "Feedback Date"],
			default: "Feedback Due Date",
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "feedback_filter",
			label: __("Feedback Filter"),
			fieldtype: "Select",
			options: ["", "Submitted Feedback", "Pending Feedback"],
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.customer_query"
				};
			}
		},
		{
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group"
		},
		{
			fieldname: "variant_of",
			label: __("Model Item Code"),
			fieldtype: "Link",
			options: "Item",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: {"is_vehicle": 1, "has_variants": 1, "include_disabled": 1}
				};
			}
		},
		{
			fieldname: "item_code",
			label: __("Variant Item Code"),
			fieldtype: "Link",
			options: "Item",
			get_query: function() {
				var variant_of = frappe.query_report.get_filter_value('variant_of');
				var filters = {"is_vehicle": 1, "include_disabled": 1};
				if (variant_of) {
					filters['variant_of'] = variant_of;
				}
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: filters
				};
			}
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group"
		},
		{
			fieldname: "project_type",
			label: __("Project Type"),
			fieldtype: "Link",
			options: "Project Type"
		},
		{
			fieldname: "project_workshop",
			label: __("Project Workshop"),
			fieldtype: "Link",
			options: "Project Workshop"
		},
	],

	onChange: function(new_value, column, data, rowIndex) {
		if (column.fieldname == "customer_feedback") {
			if (cstr(data['customer_feedback']) === cstr(new_value)) {
				return
			}

			return frappe.call({
				method: "erpnext.projects.doctype.project.project.submit_feedback",
				args: {
					project: data.project,
					customer_feedback: new_value,
				},
				callback: function(r) {
					if (!r.exc) {
						let row = frappe.query_report.datatable.datamanager.data[rowIndex];
						row.feedback_date = r.message.feedback_date;
						row.feedback_time = r.message.feedback_time;
						row.feedback_dt = r.message.feedback_dt;
						row.customer_feedback = r.message.customer_feedback;

						erpnext.utils.query_report_local_refresh()
					}
				},
			});
		}
	},
};
