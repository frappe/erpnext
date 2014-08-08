frappe.listview_settings['Sales Order'] = {
	add_fields: ["grand_total", "company", "currency", "customer",
		"customer_name", "per_delivered", "per_billed", "delivery_date"],
	filters: [["per_delivered", "<", 100]]
};
