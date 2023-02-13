// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Vehicle Maintenance Schedule"] = {
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
			fieldname: "date_type",
			label: __("Date Type"),
			fieldtype: "Select",
			options: ["Reminder Date", "Service Due Date"],
			default: "Reminder Date",
			reqd: 1,
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"project_template",
			"label": __("Project Template"),
			"fieldtype": "Link",
			"options": "Project Template"
		},
		{
			"fieldname":"project_template_category",
			"label": __("Project Template Category"),
			"fieldtype": "Link",
			"options": "Project Template Category"
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
	],

	prepare_column: function (column) {
		if (column && column.fieldname == "remarks") {
			column.custom_editor = frappe.query_reports["Vehicle Maintenance Schedule"].get_remarks_editor;
		}
	},

	get_remarks_editor: function (column, current_value, rowIndex) {
		const row_data = this.datatable.datamanager.getData(rowIndex);

		const dialog = new frappe.ui.Dialog({
			title: __('Submit Remarks'),
			doc: {},
			fields: [
				{
					fieldname: "remarks",
					fieldtype: "Small Text",
					label: __("Remarks"),
					reqd: 1
				},
				{
					fieldname: "action",
					fieldtype: "Select",
					label: __("Action"),
					reqd: 1,
					options: ["", "Schedule Follow Up", "Set As Lost", "Create Appointment"],
				},
				{fieldtype: "Section Break", depends_on: "eval:doc.action == 'Schedule Follow Up'"},
				{
					label : "Follow Up in Days",
					fieldname: "follow_up_days",
					fieldtype: "Int",
					default: 0,
					onchange: () => {
						let today = frappe.datetime.nowdate();
						let contact_date = frappe.datetime.add_days(today, dialog.get_value('follow_up_days'));
						dialog.set_value('schedule_date', contact_date);
					}
				},
				{fieldtype: "Column Break"},
				{
					label : "Schedule Date",
					fieldname: "schedule_date",
					fieldtype: "Date",
					onchange: () => {
						var today = frappe.datetime.get_today();
						var schedule_date = dialog.get_value('schedule_date');
						dialog.doc.follow_up_days = frappe.datetime.get_diff(schedule_date, today);
						dialog.get_field('follow_up_days').refresh();
					}
				},
				{fieldtype: "Section Break", depends_on: "eval:doc.action == 'Set As Lost'"},
				{
					fieldtype: "Table MultiSelect",
					label: __("Lost Reasons"),
					fieldname: "lost_reason",
					options: 'Lost Reason Detail',
				},
			],
			primary_action: (dialog_data) => {
				this.datatable.cellmanager.deactivateEditing(false);
				dialog.hide();

				return frappe.call({
					method: "erpnext.crm.doctype.opportunity.opportunity.submit_communication_with_action",
					args: {
						remarks: dialog_data.remarks,
						action: dialog_data.action,
						follow_up_date: dialog_data.schedule_date,
						lost_reason: dialog_data.lost_reason,
						opportunity: row_data.opportunity,
						maintenance_schedule: row_data.schedule,
						maintenance_schedule_row: row_data.schedule_row,
					},
					callback: function(r) {
						frappe.query_report.datatable.datamanager.data[rowIndex].contact_date = r.message.contact_date;
						frappe.query_report.datatable.datamanager.data[rowIndex].remarks = r.message.remarks;
						frappe.query_report.datatable.datamanager.data[rowIndex].opportunity = r.message.opportunity;
						erpnext.utils.query_report_local_refresh();

						if (r.message.appointment_doc) {
							frappe.model.sync(r.message.appointment_doc);
							frappe.set_route("Form", r.message.appointment_doc.doctype, r.message.appointment_doc.name);
						}
					},
					error: function() {
						erpnext.utils.query_report_local_refresh();
					},
				});
			},
			secondary_action: () => {
				this.datatable.cellmanager.deactivateEditing(false);
			}
		});
		dialog.show();
	},

	formatter: function(value, row, column, data, default_formatter) {
		var style = {};

		if (column.fieldname == "contact_date") {
			style['font-weight'] = 'bold';
		}

		return default_formatter(value, row, column, data, {css: style});
	},

	onload: function () {
		frappe.model.with_doctype("Lost Reason Detail");
	}
};
