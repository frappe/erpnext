// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Supplier Quotation Comparison"] = {
	filters: [
		{
			fieldtype: "Link",
			label: __("Company"),
			options: "Company",
			fieldname: "company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			width: "80",
			reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			width: "80",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			default: "",
			options: "Item",
			label: __("Item"),
			fieldname: "item_code",
			fieldtype: "Link",
			get_query: () => {
				let quote = frappe.query_report.get_filter_value("supplier_quotation");
				if (quote != "") {
					return {
						query: "erpnext.stock.doctype.quality_inspection.quality_inspection.item_query",
						filters: {
							from: "Supplier Quotation Item",
							parent: quote,
						},
					};
				}
			},
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("Supplier", txt);
			},
		},
		{
			fieldtype: "MultiSelectList",
			label: __("Supplier Quotation"),
			fieldname: "supplier_quotation",
			default: "",
			get_data: function (txt) {
				return frappe.db.get_link_options("Supplier Quotation", txt, { docstatus: ["<", 2] });
			},
		},
		{
			fieldtype: "Link",
			label: __("Request for Quotation"),
			options: "Request for Quotation",
			fieldname: "request_for_quotation",
			default: "",
			get_query: () => {
				return { filters: { docstatus: ["<", 2] } };
			},
		},
		{
			fieldname: "group_by",
			label: __("Group by"),
			fieldtype: "Select",
			options: [
				{ label: __("Group by Supplier"), value: "Group by Supplier" },
				{ label: __("Group by Item"), value: "Group by Item" },
			],
			default: __("Group by Supplier"),
		},
		{
			fieldtype: "Check",
			label: __("Include Expired"),
			fieldname: "include_expired",
			default: 0,
		},
	],

	formatter: (value, row, column, data, default_formatter) => {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "valid_till" && data.valid_till) {
			if (frappe.datetime.get_diff(data.valid_till, frappe.datetime.nowdate()) <= 1) {
				value = `<div style="color:red">${value}</div>`;
			} else if (frappe.datetime.get_diff(data.valid_till, frappe.datetime.nowdate()) <= 7) {
				value = `<div style="color:darkorange">${value}</div>`;
			}
		}

		if (column.fieldname === "price_per_unit" && data.price_per_unit && data.min && data.min === 1) {
			value = `<div style="color:green">${value}</div>`;
		}
		return value;
	},

	onload: (report) => {
		// Create a button for setting the default supplier
		report.page.add_inner_button(
			__("Select Default Supplier"),
			() => {
				let reporter = frappe.query_reports["Supplier Quotation Comparison"];

				//Always make a new one so that the latest values get updated
				reporter.make_default_supplier_dialog(report);
			},
			__("Tools")
		);
	},
	make_default_supplier_dialog: (report) => {
		// Get the name of the item to change
		if (!report.data) return;

		let filters = report.get_values();
		let item_code = filters.item_code;

		// Get a list of the suppliers (with a blank as well) for the user to select
		let suppliers = $.map(report.data, (row, idx) => {
			return row.supplier_name;
		});

		let items = [];
		report.data.forEach((d) => {
			if (!items.includes(d.item_code)) {
				items.push(d.item_code);
			}
		});

		// Create a dialog window for the user to pick their supplier
		let dialog = new frappe.ui.Dialog({
			title: __("Select Default Supplier"),
			fields: [
				{
					reqd: 1,
					label: "Supplier",
					fieldtype: "Link",
					options: "Supplier",
					fieldname: "supplier",
					get_query: () => {
						return {
							filters: {
								name: ["in", suppliers],
							},
						};
					},
				},
				{
					reqd: 1,
					label: "Item",
					fieldtype: "Link",
					options: "Item",
					fieldname: "item_code",
					get_query: () => {
						return {
							filters: {
								name: ["in", items],
							},
						};
					},
				},
			],
		});

		dialog.set_primary_action(__("Set Default Supplier"), () => {
			let values = dialog.get_values();

			if (values) {
				// Set the default_supplier field of the appropriate Item to the selected supplier
				frappe.call({
					method: "erpnext.buying.report.supplier_quotation_comparison.supplier_quotation_comparison.set_default_supplier",
					args: {
						item_code: values.item_code,
						supplier: values.supplier,
						company: filters.company,
					},
					freeze: true,
					callback: (r) => {
						frappe.msgprint(__("Successfully Set Supplier"));
						dialog.hide();
					},
				});
			}
		});
		dialog.show();
	},
};
