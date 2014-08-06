frappe.listview_settings['Quotation'] = {
	add_fields: ["customer_name", "quotation_to", "grand_total", "status",
		"company", "currency", "order_type", "lead", "customer"],
	filters: [["status", "=", "Submitted"]]
};
