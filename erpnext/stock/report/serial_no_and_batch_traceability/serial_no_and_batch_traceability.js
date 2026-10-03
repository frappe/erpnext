// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Serial No and Batch Traceability"] = {
	export_hidden_cols: true,
	filters: [
		{
			fieldname: "item_code",
			label: __("Item Code"),
			options: "Item",
			fieldtype: "Link",
			get_query: () => {
				return {
					query: "erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.item_query",
				};
			},
		},
		{
			fieldname: "batches",
			label: __("Batch No"),
			fieldtype: "MultiSelectList",
			options: "Batch",
			get_data: (txt) => {
				let filters = {
					disabled: 0,
				};

				let item_code = frappe.query_report.get_filter_value("item_code");
				if (item_code?.length) {
					filters.item = ["in", item_code];
				}

				return frappe.db.get_link_options("Batch", txt, filters);
			},
		},
		{
			fieldname: "serial_nos",
			label: __("Serial No"),
			fieldtype: "MultiSelectList",
			options: "Serial No",
			get_data: (txt) => {
				let filters = {};

				let item_code = frappe.query_report.get_filter_value("item_code");
				if (item_code?.length) {
					filters.item_code = ["in", item_code];
				}

				return frappe.db.get_link_options("Serial No", txt, filters);
			},
		},
		{
			fieldname: "traceability_direction",
			label: __("Tracebility Direction"),
			fieldtype: "Select",
			options: "Backward\nForward\nBoth",
			default: "Backward",
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		if (column.fieldname === "qty" && !data.item_code) {
			return "";
		}

		value = erpnext.utils.format_serial_batch_number(value, row, column, data, default_formatter);
		if (!column.serial_batch || !value) {
			return value;
		}

		const element = $("<span>").html(value);
		element.find("a").addClass(get_traceability_class(column.serial_batch, data));
		return element.html();
	},
};

function get_traceability_class(reference, data) {
	const filter = reference.doctype === "Batch" ? "batches" : "serial_nos";
	const selected = frappe.query_report.get_filter_value(filter);
	const item_code = frappe.query_report.get_filter_value("item_code");
	if (
		(selected?.length && !selected.includes(data[reference.fieldname])) ||
		(item_code && data.item_code && data.item_code !== item_code)
	) {
		return "ellipsis";
	}
	return data.direction === "Backward" ? "ellipsis text-success" : "ellipsis text-danger";
}
