// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Sales Analytics"] = {
	"filters": [
		{
			fieldname: "tree_type",
			label: __("Tree Type"),
			fieldtype: "Select",
			options: ["Customer Group", "Customer", "Item Group", "Item", "Territory", "Order Type", "Project"],
			default: "Customer",
			reqd: 1
		},
		{
			fieldname: "doc_type",
			label: __("based_on"),
			fieldtype: "Select",
			options: ["Sales Order","Delivery Note","Sales Invoice"],
			default: "Sales Invoice",
			reqd: 1
		},
		{
			fieldname: "value_quantity",
			label: __("Value Or Qty"),
			fieldtype: "Select",
			options: [
				{ "value": "Value", "label": __("Value") },
				{ "value": "Quantity", "label": __("Quantity") },
			],
			default: "Value",
			reqd: 1
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_start_date"),
			reqd: 1
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_end_date"),
			reqd: 1
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "range",
			label: __("Range"),
			fieldtype: "Select",
			options: [
				{ "value": "Weekly", "label": __("Weekly") },
				{ "value": "Monthly", "label": __("Monthly") },
				{ "value": "Quarterly", "label": __("Quarterly") },
				{ "value": "Yearly", "label": __("Yearly") }
			],
			default: "Monthly",
			reqd: 1
		}
	],
	after_datatable_render: function(datatable_obj) {
		$(datatable_obj.wrapper).find(".dt-row-0").find('input[type=checkbox]').click();
	},
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
			events: {
				onCheckRow: function (data) {
					if (!data) return;
					const data_doctype = $(
						data[2].html
					)[0].attributes.getNamedItem("data-doctype").value;
					const tree_type = frappe.query_report.filters[0].value;
					if (data_doctype != tree_type) return;

					row_name = data[2].content;
					length = data.length;

					if (tree_type == "Customer") {
						row_values = data
							.slice(4, length - 1)
							.map(function (column) {
								return column.content;
							});
					} else if (tree_type == "Item") {
						row_values = data
							.slice(5, length - 1)
							.map(function (column) {
								return column.content;
							});
					} else {
						row_values = data
							.slice(3, length - 1)
							.map(function (column) {
								return column.content;
							});
					}

					entry = {
						name: row_name,
						values: row_values,
					};

					let raw_data = frappe.query_report.chart.data;
					let new_datasets = raw_data.datasets;

					let element_found = new_datasets.some((element, index, array)=>{
						if(element.name == row_name){
							array.splice(index, 1)
							return true
						}
						return false
					})

					if (!element_found) {
						new_datasets.push(entry);
					}

					let new_data = {
						labels: raw_data.labels,
						datasets: new_datasets,
					};
					chart_options = {
						data: new_data,
						type: "line",
					};
					frappe.query_report.render_chart(chart_options);

					frappe.query_report.raw_chart_data = new_data;
				},
			},
		});
	},
}


