// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Price List Versions Report"] = {
	"filters": [

		{
			fieldname: "tree_type",
			label: __("Tree Type"),
			fieldtype: "Select",
			options: ["Item","Customer","Item Group"],
			default: "",
			reqd: 1
		},
		{
			fieldname: "doc_type",
			label: __("based_on"),
			fieldtype: "Read Only",
			default: "Item Price",
			reqd: 1
		},
		{
			fieldname: "price_list",
			label: __("Price List"),
			fieldtype: "Select",
			options: [
				{ "value": "Selling", "label": __("Selling") },
				{ "value": "Buying", "label": __("Buying") }
			],
			default: "Selling",
			reqd: 1
		},

		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_global_default("year_start_date"),
			reqd: 1
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_global_default("year_end_date"),
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
				onCheckRow: function(data) {
					row_name = data[2].content;
					row_values = data.slice(7).map(function (column) {
						return column.content;
					})
					entry  = {
						'name':row_name,
						'values':row_values
					}

					let raw_data = frappe.query_report.chart.data;
					let new_datasets = raw_data.datasets;

					var found = false;

					for(var i=0; i < new_datasets.length;i++){
						if(new_datasets[i].name == row_name){
							found = true;
							new_datasets.splice(i,1);
							break;
						}
					}

					if(!found){
						new_datasets.push(entry);
					}

					let new_data = {
						labels: raw_data.labels,
						datasets: new_datasets
					}

					setTimeout(() => {
						frappe.query_report.chart.update(new_data)
					},500)


					setTimeout(() => {
						frappe.query_report.chart.draw(true);
					}, 1000)

					frappe.query_report.raw_chart_data = new_data;
				},
			}
		});
	}
}