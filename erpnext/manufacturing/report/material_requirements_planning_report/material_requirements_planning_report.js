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
			const indexes = frappe.query_report.datatable.rowmanager.getCheckedRows();
			const selected_rows = indexes
				.map((i) => frappe.query_report.data[i])
				.filter((row) => row && row.item_code);

			if (!selected_rows.length) {
				frappe.throw(__("Please select a row to create a Reposting Entry"));
			}

			if (frappe.query_report.get_filter_value("show_in_bucket_view")) {
				frappe.throw(__("Please uncheck 'Show in Bucket View' to create Orders"));
			}

			prompt_and_make_order(selected_rows);
		});
	},
};

function items_missing_bom(selected_rows) {
	const seen = new Set();
	const items = [];
	for (const row of selected_rows) {
		if (row.type_of_material !== "Manufacture" || row.bom_no || seen.has(row.item_code)) {
			continue;
		}
		seen.add(row.item_code);
		items.push({ item_code: row.item_code, item_name: row.item_name });
	}
	return items;
}

function apply_selected_boms(selected_rows, bom_rows) {
	const bom_by_item = {};
	for (const row of bom_rows || []) {
		if (row.item_code && row.bom_no) {
			bom_by_item[row.item_code] = row.bom_no;
		}
	}
	for (const row of selected_rows) {
		if (!row.bom_no && bom_by_item[row.item_code]) {
			row.bom_no = bom_by_item[row.item_code];
		}
	}
}

function prompt_and_make_order(selected_rows) {
	const missing_bom = items_missing_bom(selected_rows);
	const fields = [
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
	];

	if (missing_bom.length) {
		fields.push({
			label: __("Select BOM"),
			fieldtype: "Table",
			fieldname: "boms",
			reqd: 1,
			cannot_add_rows: true,
			cannot_delete_rows: true,
			in_place_edit: true,
			description: __("These items have no default BOM. Select one to create Work Orders."),
			data: missing_bom,
			get_data: () => missing_bom,
			fields: [
				{
					fieldtype: "Link",
					fieldname: "item_code",
					options: "Item",
					label: __("Item Code"),
					in_list_view: 1,
					read_only: 1,
				},
				{
					fieldtype: "Data",
					fieldname: "item_name",
					label: __("Item Name"),
					in_list_view: 1,
					read_only: 1,
				},
				{
					fieldtype: "Link",
					fieldname: "bom_no",
					options: "BOM",
					reqd: 1,
					label: __("BOM"),
					in_list_view: 1,
					get_query: (doc) => ({
						query: "erpnext.controllers.queries.bom",
						filters: { item: doc.item_code },
					}),
				},
			],
		});
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Make Purchase / Work Order"),
		fields: fields,
		primary_action_label: __("Create"),
		primary_action(values) {
			if (missing_bom.length) {
				const bom_rows = dialog.fields_dict.boms.grid.get_data();
				const without_bom = bom_rows.filter((row) => !row.bom_no);
				if (without_bom.length) {
					frappe.msgprint(
						__("Please select a BOM for {0}", [
							without_bom.map((row) => row.item_code).join(", "),
						])
					);
					return;
				}
				apply_selected_boms(selected_rows, bom_rows);
			}

			dialog.hide();
			frappe.call({
				method: "erpnext.manufacturing.report.material_requirements_planning_report.material_requirements_planning_report.make_order",
				freeze: true,
				args: {
					selected_rows: selected_rows,
					company: frappe.query_report.get_filter_value("company"),
					warehouse: values.use_default_warehouse ? null : values.warehouse,
					mps: frappe.query_report.get_filter_value("mps"),
				},
				callback: function (r) {
					if (r.message) {
						frappe.set_route("List", r.message);
					}
				},
			});
		},
	});
	dialog.show();
}
