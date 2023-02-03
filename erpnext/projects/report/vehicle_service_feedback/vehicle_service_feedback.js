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
			options: ["Feedback Due Date", "Feedback Date", "Contact Date"],
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
		{
			fieldname: "reference_ro",
			label: __("Reference RO"),
			fieldtype: "Select",
			options: [
				"",
				{ "value": "has_reference", "label": __("Has Reference RO #") },
				{ "value": "has_no_reference", "label": __("Has No Reference RO #") }
			],
		},
	],

	onChange: function(new_value, column, data, rowIndex) {
		if (in_list(["customer_feedback", "contact_remarks"], column.fieldname)) {
			if (cstr(data[column.fieldname]) == cstr(new_value)) return

			return frappe.call({
				method: "erpnext.crm.doctype.customer_feedback.customer_feedback.submit_customer_feedback",
				args: {
					reference_doctype: "Project",
					reference_name: data.project,
					feedback_or_remark: column.fieldname == "customer_feedback" ? "Feedback": "Remarks",
					message: new_value,
				},
				callback: function(r) {
					if (!r.exc) {
						let row = frappe.query_report.datatable.datamanager.data[rowIndex];
						row[column.fieldname] = r.message[column.fieldname];
						if (column.fieldname == "customer_feedback") {
							row.feedback_dt = r.message.feedback_dt;
						} else {
							row.contact_dt = r.message.contact_dt;
						}

						erpnext.utils.query_report_local_refresh();
					}
				}
			})
		}
	},
};
