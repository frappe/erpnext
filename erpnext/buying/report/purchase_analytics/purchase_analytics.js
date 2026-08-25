// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Analytics"] = {
	filters: [
		{
			fieldname: "tree_type",
			label: __("Tree Type"),
			fieldtype: "Select",
			options: ["Supplier Group", "Supplier", "Item Group", "Item"],
			default: "Supplier",
			reqd: 1,
		},
		{
			fieldname: "doc_type",
			label: __("based_on"),
			fieldtype: "Select",
			options: ["Purchase Order", "Purchase Receipt", "Purchase Invoice"],
			default: "Purchase Invoice",
			reqd: 1,
		},
		{
			fieldname: "value_quantity",
			label: __("Value Or Qty"),
			fieldtype: "Select",
			options: [
				{ value: "Value", label: __("Value") },
				{ value: "Quantity", label: __("Quantity") },
			],
			default: "Value",
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2],
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "range",
			label: __("Range"),
			fieldtype: "Select",
			options: [
				{ value: "Weekly", label: __("Weekly") },
				{ value: "Monthly", label: __("Monthly") },
				{ value: "Quarterly", label: __("Quarterly") },
				{ value: "Yearly", label: __("Yearly") },
			],
			default: "Monthly",
			reqd: 1,
		},
		{
			fieldname: "show_aggregate_value_from_subsidiary_companies",
			label: __("Show Aggregate Value from Subsidiary Companies"),
			fieldtype: "Check",
		},
	],
	build_chart_data(row_indices) {
		const chart_data = frappe.query_report.chart_options.data;

		return {
			labels: chart_data.labels,
			datasets: row_indices.map((row_index) => chart_data.datasets[row_index]).filter(Boolean),
		};
	},
	sync_chart(datatable) {
		const visible_rows = datatable.purchase_analytics_visible_rows.map(Number);
		const visible_row_set = new Set(visible_rows);
		const checked_rows = datatable.rowmanager
			.getCheckedRows()
			.map(Number)
			.filter((row_index) => visible_row_set.has(row_index));
		const chart_data = this.build_chart_data(checked_rows.length ? checked_rows : visible_rows);
		const chart_options = Object.assign({}, frappe.query_report.chart_options, {
			data: chart_data,
		});

		frappe.query_report.render_chart(chart_options);
		frappe.query_report.raw_chart_data = chart_data;
	},
	after_datatable_render(datatable) {
		clearTimeout(datatable.purchase_analytics_chart_update);
		datatable.rowmanager.checkMap = [];
		datatable.purchase_analytics_visible_rows = datatable.datamanager.getAllRowIndices();
		if (datatable.purchase_analytics_filter_rows) return;

		// DataTable does not expose a filter event, so use its resolved visible row indices.
		const filter_rows = datatable.datamanager.filterRows.bind(datatable.datamanager);
		datatable.purchase_analytics_filter_rows = filter_rows;
		datatable.datamanager.filterRows = (...args) =>
			filter_rows(...args).then((result) => {
				datatable.purchase_analytics_visible_rows = result.rowsToShow;
				this.sync_chart(datatable);
				return result;
			});
	},
	get_datatable_options(options) {
		const report_settings = this;

		return Object.assign(options, {
			checkboxColumn: true,
			events: {
				onCheckRow() {
					const datatable = frappe.query_report.datatable;
					clearTimeout(datatable.purchase_analytics_chart_update);
					datatable.purchase_analytics_chart_update = setTimeout(() => {
						report_settings.sync_chart(datatable);
					});
				},
			},
		});
	},
};
