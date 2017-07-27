// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Quoted Item Comparison"] = {
	"filters": [
		{
			"fieldname": "supplier_quotation",
			"label": __("Supplier Quotation"),
			"fieldtype": "Link",
			"options": "Supplier Quotation",
			"default": "",
			"get_query": function () {
				return { filters: { "docstatus": ["<", 2] } }
			}
		},
		{
			"fieldname": "item",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"default": "",
			"reqd": 1,
			"get_query": function () {
				var quote = frappe.query_report_filters_by_name.supplier_quotation.get_value();
				if (quote != "") {
					return {
						query: "erpnext.buying.doctype.quality_inspection.quality_inspection.item_query",
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
	onload: function (report) {
		// Create a button for setting the default supplier
		report.page.add_inner_button(__("Select Default Supplier"), function () {

			var reporter = frappe.query_reports["Quoted Item Comparison"];

			//Always make a new one so that the latest values get updated
			reporter.make_default_supplier_dialog(report);
			report.dialog.show();
			setTimeout(function () { report.dialog.input.focus(); }, 1000);

		}, 'Tools');

	},
	"make_default_supplier_dialog": function (report) {
		// Get the name of the item to change
		var filters = report.get_values();
		var item_code = filters.item;

		// Get a list of the suppliers (with a blank as well) for the user to select
		var select_options = "";
		for (let supplier of report.data) {
			select_options += supplier.supplier_name + '\n'
		}

		// Create a dialog window for the user to pick their supplier
		var d = new frappe.ui.Dialog({
			title: __('Select Default Supplier'),
			fields: [
				{ fieldname: 'supplier', fieldtype: 'Select', label: 'Supplier', reqd: 1, options: select_options },
				{ fieldname: 'ok_button', fieldtype: 'Button', label: 'Set Default Supplier' },
			]
		});

		// On the user clicking the ok button
		d.fields_dict.ok_button.input.onclick = function () {
			var btn = d.fields_dict.ok_button.input;
			var v = report.dialog.get_values();
			if (v) {
				$(btn).set_working();

				// Set the default_supplier field of the appropriate Item to the selected supplier
				frappe.call({
					method: "frappe.client.set_value",
					args: {
						doctype: "Item",
						name: item_code,
						fieldname: "default_supplier",
						value: v.supplier,
					},
					callback: function (r) {
						$(btn).done_working();
						frappe.msgprint("Successfully Set Supplier");
						report.dialog.hide();
					}
				});
			}
		}
		report.dialog = d;
	}
}


