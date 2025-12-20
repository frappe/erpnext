// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Serial No and Batch Traceability"] = {
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

		return custom_formatter(value, row, column, data, default_formatter);
	},
};

function getTraceabilityLink({ type, value, original_value, item_code, data, filter_values }) {
	if (!value) return value;

	const base_url = type === "batch_no" ? "/app/batch/" : "/app/serial-no/";
	const filter_list = filter_values[type]; // either batches or serial_nos

	let css_class = "ellipsis";

	if (filter_list?.length && !filter_list.includes(original_value)) {
		// value not in filtered list
		css_class = "ellipsis";
	} else if (item_code && data.item_code && data.item_code !== item_code) {
		// mismatch in item code
		css_class = "ellipsis";
	} else {
		// color by direction
		css_class = data.direction === "Backward" ? "ellipsis text-success" : "ellipsis text-danger";
	}

	return `<a class="${css_class}" href="${base_url}${original_value}">${original_value}</a>`;
}

function custom_formatter(value, row, column, data, default_formatter) {
	let original_value = value;
	let filter_values = {
		batch_no: frappe.query_report.get_filter_value("batches"),
		serial_no: frappe.query_report.get_filter_value("serial_nos"),
	};
	let item_code = frappe.query_report.get_filter_value("item_code");

	value = default_formatter(value, row, column, data);

	if (["batch_no", "serial_no"].includes(column.fieldname) && value) {
		value = getTraceabilityLink({
			type: column.fieldname,
			value,
			original_value,
			item_code,
			data,
			filter_values,
		});
	}

	return value;
}
