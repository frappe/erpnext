// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Quoted Item Comparison"] = {
	filters: [
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
			reqd: 1,
			default: "",
			options: "Item",
			label: __("Item"),
			fieldname: "item",
			fieldtype: "Link",
			get_query: () => {
				let quote = frappe.query_report_filters_by_name.supplier_quotation.get_value();
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
		}
	],
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
						frappe.msgprint("Successfully Set Supplier");
						dialog.hide();
					}
				});
			}
		});
		dialog.show();
	}
}


