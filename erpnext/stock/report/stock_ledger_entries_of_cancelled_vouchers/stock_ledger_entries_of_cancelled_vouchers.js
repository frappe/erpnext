// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Ledger Entries of Cancelled Vouchers"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "voucher_type",
			label: __("Voucher Type"),
			fieldtype: "Link",
			options: "DocType",
			get_query: () => ({
				filters: { is_submittable: 1 },
			}),
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
			fieldtype: "Link",
			options: "Warehouse",
		},
	],

	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},

	onload(report) {
		report.page.add_inner_button(__("Cancel Stock Ledger Entries"), () => {
			let indexes = frappe.query_report.datatable.rowmanager.getCheckedRows();
			let selected_rows = indexes.map((i) => frappe.query_report.data[i]);

			if (!selected_rows.length) {
				frappe.throw(__("Please select at least one row to fix"));
			}

			frappe.confirm(
				__(
					"All Stock Ledger Entries and Serial and Batch Bundles of the selected vouchers will be cancelled and reposting will be queued. Continue?"
				),
				() => {
					frappe.call({
						method: "erpnext.stock.report.stock_ledger_entries_of_cancelled_vouchers.stock_ledger_entries_of_cancelled_vouchers.fix_uncancelled_entries",
						freeze: true,
						args: {
							selected_rows: selected_rows,
						},
						callback: function () {
							frappe.query_report.refresh();
						},
					});
				}
			);
		});
	},
};
