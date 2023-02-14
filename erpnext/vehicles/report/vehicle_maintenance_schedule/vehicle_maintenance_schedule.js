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
			options: ["Follow Up Date", "Service Due Date"],
			default: "Follow Up Date",
			reqd: 1,
		},
		{
			fieldname:"from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname:"project_template",
			label: __("Project Template"),
			fieldtype: "Link",
			options: "Project Template"
		},
		{
			fieldname: "project_template_category",
			label: __("Project Template Category"),
			fieldtype: "Link",
			options: "Project Template Category"
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
			fieldname: "opportunity",
			label: __("Opportunity"),
			fieldtype: "Link",
			options: "Opportunity"
		},
	],

	prepare_column: function (column) {
		if (column && column.is_communication) {
			column.custom_editor = frappe.query_reports["Vehicle Maintenance Schedule"].get_remarks_editor;
		}
	},

	get_remarks_editor: function (column, current_value, rowIndex) {
		const row_data = this.datatable.datamanager.getData(rowIndex);
		this.datatable.cellmanager.deactivateEditing(false);

		if (["Lost", "Closed"].includes(row_data.status)) {
			frappe.msgprint(__("Cannot submit communication because Opportunity is {0}", [row_data.status]));
			return;
		}

		const dialog = new frappe.ui.Dialog({
			title: __('Submit Communication'),
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
					options: ["", "Submit Remarks Only", "Schedule Follow Up", "Mark As Lost", "Mark As Closed", "Create Appointment"],
					onchange: () => {
						let is_followup = dialog.get_value("action") == "Schedule Follow Up";
						let is_lost = dialog.get_value("action") == "Mark As Lost";

						dialog.set_df_property("schedule_date", "reqd", is_followup ? 1 : 0);
						dialog.set_df_property("follow_up_days", "reqd", is_followup ? 1 : 0);

						dialog.set_df_property("lost_reason", "reqd", is_lost ? 1 : 0);
					}
				},
				{fieldtype: "Section Break", depends_on: "eval:doc.action == 'Schedule Follow Up'"},
				{
					label : "Follow Up in Days",
					fieldname: "follow_up_days",
					fieldtype: "Int",
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
				{fieldtype: "Section Break", depends_on: "eval:doc.action == 'Mark As Lost'"},
				{
					fieldtype: "Table MultiSelect",
					label: __("Lost Reasons"),
					fieldname: "lost_reason",
					options: 'Lost Reason Detail',
				},
				{fieldtype: "Section Break"},
				{
					fieldname: "customer",
					fieldtype: "Link",
					options: "Customer",
					label: __("Customer"),
					read_only: 1,
					default: row_data.customer,
				},
				{
					fieldname: "contact_no",
					fieldtype: "Data",
					label: __("Contact No"),
					read_only: 1,
					default: row_data.contact_no,
				},
				{fieldtype: "Column Break"},
				{
					fieldname: "customer_name",
					fieldtype: "Data",
					label: __("Customer Name"),
					read_only: 1,
					default: row_data.customer_name,
				},
				{fieldtype: "Section Break"},
				{
					fieldname: "template_name",
					fieldtype: "Data",
					label: __("Maintenance Type"),
					read_only: 1,
					default: row_data.project_template_name,
				},
				{fieldtype: "Column Break"},
				{
					fieldname: "due_date",
					fieldtype: "Date",
					label: __("Due Date"),
					read_only: 1,
					default: row_data.due_date,
				},
				{fieldtype: "Section Break"},
				{
					fieldname: "vehicle",
					fieldtype: "Link",
					options: "Vehicle",
					label: __("Vehicle"),
					read_only: 1,
					default: row_data.vehicle,
				},
				{
					fieldname: "license_plate",
					fieldtype: "Data",
					label: __("Registration #"),
					read_only: 1,
					default: row_data.license_plate,
				},
				{
					fieldname: "delivery_date",
					fieldtype: "Date",
					label: __("Delivery Date"),
					read_only: 1,
					default: row_data.delivery_date,
				},
				{fieldtype: "Column Break"},
				{
					fieldname: "item_code",
					fieldtype: "Data",
					label: __("Variant Code"),
					read_only: 1,
					default: row_data.item_code,
				},
				{
					fieldname: "chassis_no",
					fieldtype: "Data",
					label: __("Chassis #"),
					read_only: 1,
					default: row_data.chassis_no,
				},
				{
					fieldname: "age",
					fieldtype: "Data",
					label: __("Age"),
					read_only: 1,
					default: row_data.age,
				},
			],
			primary_action: (dialog_data) => {
				dialog.hide();

				return frappe.call({
					method: "erpnext.vehicles.report.vehicle_maintenance_schedule.vehicle_maintenance_schedule.submit_communication_with_action",
					args: {
						remarks: dialog_data.remarks,
						action: dialog_data.action,
						follow_up_date: dialog_data.schedule_date,
						lost_reason: dialog_data.lost_reason,
						opportunity: row_data.opportunity,
						maintenance_schedule: row_data.maintenance_schedule,
						maintenance_schedule_row: row_data.maintenance_schedule_row,
						filters: frappe.query_report.get_filter_values(),
					},
					callback: function(r) {
						if (r.message && !r.exc) {
							if (r.message.updated_row) {
								frappe.query_report.datatable.datamanager.data[rowIndex] = r.message.updated_row;
								erpnext.utils.query_report_local_refresh();
							}

							if (r.message.appointment_doc) {
								frappe.model.sync(r.message.appointment_doc);
								frappe.set_route("Form", r.message.appointment_doc.doctype, r.message.appointment_doc.name);
							}
						}
					},
					error: function() {
						erpnext.utils.query_report_local_refresh();
					},
				});
			}
		});
		dialog.show();
	},

	formatter: function(value, row, column, data, default_formatter) {
		let style = {};

		if (column.is_communication == "communcation_date") {
			style['font-weight'] = 'bold';
		}

		if (["Lost", "Closed"].includes(data.status)) {
			style['color'] = "#858585";
		}

		if (column.fieldname == 'status') {
			style['font-weight'] = 'bold';
			if (value == "Open") {
				style['color'] = "orange";
			} else if (value == "To Follow Up") {
				style['color'] = "blue";
			} else if (value == "Replied") {
				style['color'] = "purple";
			} else if (value == "Converted") {
				style['color'] = "green";
			}
		}

		return default_formatter(value, row, column, data, {css: style});
	},

	onload: function () {
		frappe.model.with_doctype("Lost Reason Detail");
	}
};
