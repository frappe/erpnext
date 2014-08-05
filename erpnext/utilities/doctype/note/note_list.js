frappe.listview_settings['Note'] = {
	add_fields: ["title", "public"],
	set_title_left: function() {
		frappe.set_route();
	}
}
