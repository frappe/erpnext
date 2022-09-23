frappe.query_reports["BOM Stock Report"] = {
	"filters": [
		{
			"fieldname": "bom",
			"label": __("BOM"),
			"fieldtype": "Link",
			"options": "BOM",
			"reqd": 1
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
		},
		{
			"fieldname": "qty_to_produce",
			"label": __("Quantity to Produce"),
			"fieldtype": "Float",
			"default": 1
		 },
		{
			"fieldname": "show_exploded_view",
			"label": __("Show Exploded View"),
			"fieldtype": "Check"
		},
	],
	formatter: function(value, row, column, data, default_formatter) {
		var style = {};

		if (["item_code", "producible_qty"].includes(column.fieldname)) {
			if (flt(data["producible_qty"]) > 0) {
				style['color'] = 'green';
			} else {
				style['color'] = 'red';
			}
		}

		return default_formatter(value, row, column, data, {css: style});
	}
}
