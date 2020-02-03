frappe.listview_settings['Customer'] = {
	add_fields: ["customer_name", "territory", "customer_group", "customer_type", "image"],

	onload: function(listview) {
		frappe.route_options = {
			"customer_group": "",
			"territory": ""
		};
	}
};
