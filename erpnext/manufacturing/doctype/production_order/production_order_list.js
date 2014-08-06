frappe.listview_settings['Production Order'] = {
	add_fields: ["bom_no", "status", "sales_order", "qty",
		"produced_qty", "expected_delivery_date"],
	filters: [["status", "!=", "Completed"], ["status", "!=", "Stopped"]]
};
