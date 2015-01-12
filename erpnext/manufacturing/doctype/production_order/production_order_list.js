frappe.listview_settings['Production Order'] = {
	add_fields: ["bom_no", "status", "sales_order", "qty",
		"produced_qty", "expected_delivery_date"],
	filters: [["status", "!=", "Completed"], ["status", "!=", "Stopped"]],
	get_indicator: function(doc) {
		return [__(doc.status), {
			"Draft": "red",
			"Submitted": "blue",
			"Stopped": "red",
			"In Process": "orange",
			"Completed": "green",
			"Cancelled": "darkgrey"
		}[doc.status], "status,=," + doc.status];
	}
};
