// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Incorrect Serial and Batch Bundle"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "MultiSelectList",
			options: "Warehouse",
			get_data: function (txt) {
				let company = frappe.query_report.get_filter_value("company");
				return frappe.db.get_link_options("Warehouse", txt, company ? { company } : {});
			},
		},
	],

	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},

	onload(report) {
		report.page
			.add_inner_button(__("Fix SABB Entry"), () => {
				let indexes = frappe.query_report.datatable.rowmanager.getCheckedRows();
				let selected_rows = indexes.map((i) => frappe.query_report.data[i]);

				if (!selected_rows.length) {
					frappe.throw(__("Please select at least one row to fix"));
				} else {
					frappe.call({
						method: "erpnext.stock.report.incorrect_serial_and_batch_bundle.incorrect_serial_and_batch_bundle.fix_sabb_entries",
						freeze: true,
						args: {
							selected_rows: selected_rows,
						},
						callback: function (r) {
							frappe.query_report.refresh();
						},
					});
				}
			})
			.addClass("btn-primary");
	},
};
