// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Analytics"] = {
	// "All" reports on every doctype at once and forces the tree to Customer
	entity_tree_type() {
		const doc_type = frappe.query_report.get_filter_value("doc_type");
		return doc_type === "All" ? "Customer" : frappe.query_report.get_filter_value("tree_type");
	},
	reset_entity_filter() {
		const entity_filter = frappe.query_report.get_filter("entity");
		if (!entity_filter) return;
		entity_filter.df.label = __(this.entity_tree_type());
		entity_filter.set_value([]);
		entity_filter.refresh();
	},
	filters: [
		{
			fieldname: "tree_type",
			label: __("Tree Type"),
			fieldtype: "Select",
			options: [
				"Customer Group",
				"Customer",
				"Item Group",
				"Item",
				"Territory",
				"Order Type",
				"Project",
			],
			default: "Customer",
			reqd: 1,
			on_change: function () {
				frappe.query_reports["Sales Analytics"].reset_entity_filter();
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "entity",
			label: __("Entity"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				const tree_type = frappe.query_reports["Sales Analytics"].entity_tree_type();
				if (!tree_type || tree_type === "Order Type") return [];
				return frappe.db.get_link_options(tree_type, txt);
			},
			depends_on: "eval:doc.tree_type != 'Order Type'",
		},
		{
			fieldname: "doc_type",
			label: __("Based On"),
			fieldtype: "Select",
			options: [
				"All",
				"Quotation",
				"Sales Order",
				"Delivery Note",
				"Sales Invoice",
				"Sales Invoice (due)",
				"Payment Entry",
			],
			default: "Sales Invoice",
			reqd: 1,
			on_change: function () {
				frappe.query_reports["Sales Analytics"].reset_entity_filter();
				frappe.query_report.refresh();
			},
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
			default:
				frappe.defaults.get_user_default("sales_start_date") ||
				erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default:
				frappe.defaults.get_user_default("sales_end_date") ||
				erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2],
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
			fieldname: "curves",
			label: __("Curves"),
			fieldtype: "Select",
			options: [
				{ value: "select", label: __("Select") },
				{ value: "all", label: __("All") },
				{ value: "non-zeros", label: __("Non-Zeros") },
				{ value: "total", label: __("Total Only") },
			],
			default: "select",
			reqd: 1,
		},
		{
			fieldname: "show_aggregate_value_from_subsidiary_companies",
			label: __("Show Aggregate Value from Subsidiary Companies"),
			fieldtype: "Check",
		},
	],
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
			events: {
				onCheckRow: function (data) {
					if (!data) return;
					const data_doctype = $(data[2].html)[0].attributes.getNamedItem("data-doctype").value;
					const tree_type = frappe.query_report.filters[0].value;
					if (data_doctype != tree_type) return;

					const row_name = data[2].content;
					const raw_data = frappe.query_report.chart.data;
					const new_datasets = raw_data.datasets;
					const element_found = new_datasets.some((element, index, array) => {
						if (element.name == row_name) {
							array.splice(index, 1);
							return true;
						}
						return false;
					});
					const slice_at = { Customer: 4, Item: 5 }[tree_type] || 3;

					if (!element_found) {
						new_datasets.push({
							name: row_name,
							values: data.slice(slice_at, data.length - 1).map((column) => column.content),
						});
					}

					const new_data = {
						labels: raw_data.labels,
						datasets: new_datasets,
					};
					const new_options = Object.assign({}, frappe.query_report.chart_options, {
						data: new_data,
					});
					frappe.query_report.render_chart(new_options);

					frappe.query_report.raw_chart_data = new_data;
				},
			},
		});
	},
};
