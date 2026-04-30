// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Material Requirements Planning Report"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), 7),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), 3),
			reqd: 1,
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
			get_query: function () {
				return {
					filters: {
						is_stock_item: 1,
					},
				};
			},
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			reqd: 1,
			default: frappe.defaults.get_user_default("Warehouse"),
		},
		{
			fieldname: "mps",
			label: __("MPS"),
			fieldtype: "Link",
			options: "Master Production Schedule",
			reqd: 1,
			on_change() {
				let mps = frappe.query_report.get_filter_value("mps");
				if (mps) {
					frappe.call({
						method: "erpnext.manufacturing.doctype.master_production_schedule.master_production_schedule.get_mps_details",
						args: {
							mps: mps,
						},
						callback: function (r) {
							if (r.message) {
								frappe.query_report.set_filter_value("from_date", r.message.from_date);
								frappe.query_report.set_filter_value("to_date", r.message.to_date);
							}
						},
					});
				}
			},
		},
		{
			fieldname: "type_of_material",
			label: __("Type of Material"),
			fieldtype: "Select",
			default: "All",
			options: "\nFinished Goods\nRaw Materials\nAll",
		},
		{
			fieldname: "add_safety_stock",
			label: __("Add Safety Stock"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "show_in_bucket_view",
			label: __("Show in Bucket View"),
			fieldtype: "Check",
		},
		{
			fieldname: "bucket_view",
			label: __("View Data Based on"),
			fieldtype: "Select",
			options: "Delivery Date\nRelease Date",
			default: "Delivery Date",
			depends_on: "eval:doc.show_in_bucket_view == 1",
		},
		{
			fieldname: "bucket_size",
			label: __("Bucket Size"),
			fieldtype: "Select",
			default: "Monthly",
			options: "Daily\nWeekly\nMonthly",
			depends_on: "eval:doc.show_in_bucket_view == 1",
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		if (column.fieldtype === "Float" && !data.item_code) {
			return "";
		}

		value = default_formatter(value, row, column, data);
		// if (column.fieldname === "release_date") {
		// 	if (frappe.datetime.get_day_diff(data.release_date, frappe.datetime.get_today()) < 0) {
		// 		return `<span class="text-danger">${value}</span>`;
		// 	}
		// }

		return value;
	},

	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},

	onload(report) {
		report.page.add_inner_button(__("Make Purchase / Work Order"), () => {
			let indexes = frappe.query_report.datatable.rowmanager.getCheckedRows();
			let selected_rows = indexes.map((i) => frappe.query_report.data[i]);

			if (!selected_rows.length) {
				frappe.throw(__("Please select a row to create a Reposting Entry"));
			} else {
				let show_in_bucket_view = frappe.query_report.get_filter_value("show_in_bucket_view");
				if (show_in_bucket_view) {
					frappe.throw(__("Please uncheck 'Show in Bucket View' to create Orders"));
				}

				frappe.prompt(
					[
						{
							fieldname: "use_default_warehouse",
							label: __("Use Default Warehouse"),
							fieldtype: "Check",
							default: 1,
						},
						{
							fieldname: "warehouse",
							label: __("Warehouse"),
							fieldtype: "Link",
							options: "Warehouse",
							depends_on: "eval:!doc.use_default_warehouse",
							mandatory_depends_on: "eval:!doc.use_default_warehouse",
						},
					],
					(prompt_data) => {
						frappe.call({
							method: "erpnext.manufacturing.report.material_requirements_planning_report.material_requirements_planning_report.make_order",
							freeze: true,
							args: {
								selected_rows: selected_rows,
								company: frappe.query_report.get_filter_value("company"),
								warehouse: !prompt_data.use_default_warehouse ? prompt_data.warehouse : null,
								mps: frappe.query_report.get_filter_value("mps"),
							},
							callback: function (r) {
								if (r.message) {
									frappe.set_route("List", r.message);
								}
							},
						});
					}
				);
			}
		});
	},
};
