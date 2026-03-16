// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Pending Workflow"] = {
	filters: [
		{
			fieldname: "user",
			label: __("User"),
			fieldtype: "Link",
			options: "User",
			default: frappe.session.user,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "reference_doctype",
			label: __("DocType"),
			fieldtype: "Link",
			options: "DocType",
		},
		{
			fieldname: "workflow_state",
			label: __("Status"),
			fieldtype: "Link",
			options: "Workflow State"
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date"
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date"
		},
		{
			fieldname: "workflow_action",
			label: __("Workflow Action"),
			fieldtype: "Link",
			options: "Workflow Action Master",
			reqd: 1,
		},
	],

	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},
	
	onload: function(report) {
		report.page.add_inner_button(__("Apply Workflow Action"), () => {

			let indexes = report.datatable.rowmanager.getCheckedRows();
			let selected_rows = indexes.map(i => report.data[i]);
			let action = report.get_filter_value("workflow_action");

			if (!selected_rows.length) {
				frappe.throw(__("Please select at least one document to perform {0} action.", [action]));
			}
			
			frappe.confirm(__("Are you sure you want to perform {0} action on selected document(s)?", [action]),
				() => {
					let docs = selected_rows.map(row => ({
						doctype: row.reference_doctype,
						name: row.reference_name
					}));

					frappe.call({
						method: "erpnext.setup.report.pending_workflow.pending_workflow.apply_workflow_action",
						args: {
							rows: docs,
							action: action,
						},
						freeze: true,
						freeze_message: __("Applying workflow action..."),
						callback: function(r) {
							if (r.exc) {
								return;
							}
							frappe.show_alert({
								message: __("{0} successfully applied.", [action]),
								indicator: "green"
							});
							
							if (report.datatable) {
								report.datatable.rowmanager.checkAll(false);
							}

							report.refresh();
						}
					});
				}
			);
		});

		frappe.db.get_list("Workflow", {
			fields: ["document_type"],
			filters: { is_active: 1 },
		}).then(r => {
			let doctypes = r.map(d => d.document_type);

			report.get_filter("reference_doctype").get_query = function() {
				return {
					filters: {
						name: ["in", doctypes]
					}
				};
			};
		});
	},

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.bold) {
			value = value.bold();
		}
		return value;
	},
};