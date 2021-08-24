// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Production Plan Summary"] = {
	"filters": [
		{
			fieldname: "production_plan",
			label: __("Production Plan"),
			fieldtype: "Link",
			options: "Production Plan",
			reqd: 1,
			get_query: function() {
				return {
					filters: {
						"docstatus": 1
					}
				};
			}
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname == "document_name") {
			var color = data.pending_qty > 0 ? 'red': 'green';
			value = `<a style='color:${color}' href="#Form/${data['document_type']}/${data['document_name']}" data-doctype="${data['document_type']}">${data['document_name']}</a>`;
		}

		return value;
	},
};
