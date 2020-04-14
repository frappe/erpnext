// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Quoted Item Comparison"] = {
	filters: [
		{
			fieldtype: "Link",
			label: __("Company"),
			options: "Company",
			fieldname: "company",
			default: frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			reqd: 1,
			default: "",
			options: "Item",
			label: __("Item"),
			fieldname: "item",
			fieldtype: "Link",
			get_query: () => {
				let quote = frappe.query_report.get_filter_value('supplier_quotation');
				if (quote != "") {
					return {
						query: "erpnext.stock.doctype.quality_inspection.quality_inspection.item_query",
						filters: {
							"from": "Supplier Quotation Item",
							"parent": quote
						}
					}
				}
				else {
					return {
						filters: { "disabled": 0 }
					}
				}
			}
		},
		{
			fieldtype: "Link",
			label: __("Supplier Quotation"),
			options: "Supplier Quotation",
			fieldname: "supplier_quotation",
			default: "",
			get_query: () => {
				return { filters: { "docstatus": ["<", 2] } }
			}
		},
		{
			fieldtype: "Link",
			label: __("Request for Quotation"),
			options: "Request for Quotation",
			fieldname: "request_for_quotation",
			default: "",
			get_query: () => {
				return { filters: { "docstatus": ["<", 2] } }
			}
		}
	],

	prepare_chart_data: (result) => {
		let supplier_wise_map = {}, data_points_map = {};
		let qty_list = result.map(res=> res.qty);
		qty_list = new Set(qty_list);

		// create supplier wise map like in Report
		for(let res of result){
			if(!(res.supplier in supplier_wise_map)){
				supplier_wise_map[res.supplier]= {};
			}
			supplier_wise_map[res.supplier][res.qty] = res.price;
		}

		// create  datapoints for each qty
		for(let supplier of Object.keys(supplier_wise_map)) {
			let row = supplier_wise_map[supplier];
			for(let qty of qty_list){
				if(!data_points_map[qty]){
					data_points_map[qty] = []
				}
				if(row[qty]){
					data_points_map[qty].push(row[qty]);
				}
				else{
					data_points_map[qty].push(null);
				}
			}
		}

		let dataset = [];
		qty_list.forEach((qty) => {
			let datapoints = {
				'name': 'Price for Qty ' + qty,
				'values': data_points_map[qty]
			}
			dataset.push(datapoints);

		});
		return dataset;
	},

	get_chart_data: function (columns, result) {
		let suppliers = result.filter(d => d.supplier_name).map(res => res.supplier_name);
		let dataset = frappe.query_reports["Quoted Item Comparison"].prepare_chart_data(result);

		return {
			data: {
				labels: suppliers,
				datasets: dataset
			},
			type: 'bar'
		}
	},

	onload: (report) => {
		// Create a button for setting the default supplier
		report.page.add_inner_button(__("Select Default Supplier"), () => {
			let reporter = frappe.query_reports["Quoted Item Comparison"];

			//Always make a new one so that the latest values get updated
			reporter.make_default_supplier_dialog(report);
		}, 'Tools');

	},
	make_default_supplier_dialog: (report) => {
		// Get the name of the item to change
		if(!report.data) return;

		let filters = report.get_values();
		let item_code = filters.item;

		// Get a list of the suppliers (with a blank as well) for the user to select
		let suppliers = $.map(report.data, (row, idx)=>{ return row.supplier_name })

		// Create a dialog window for the user to pick their supplier
		let dialog = new frappe.ui.Dialog({
			title: __('Select Default Supplier'),
			fields: [
				{
					reqd: 1,
					label: 'Supplier',
					fieldtype: 'Link',
					options: 'Supplier',
					fieldname: 'supplier',
					get_query: () => {
						return {
							filters: {
								'name': ['in', suppliers]
							}
						}
					}
				}
			]
		});

		dialog.set_primary_action("Set Default Supplier", () => {
			let values = dialog.get_values();
			if(values) {
				// Set the default_supplier field of the appropriate Item to the selected supplier
				frappe.call({
					method: "frappe.client.set_value",
					args: {
						doctype: "Item",
						name: item_code,
						fieldname: "default_supplier",
						value: values.supplier,
					},
					freeze: true,
					callback: (r) => {
						frappe.msgprint(__("Successfully Set Supplier"));
						dialog.hide();
					}
				});
			}
		});
		dialog.show();
	}
}