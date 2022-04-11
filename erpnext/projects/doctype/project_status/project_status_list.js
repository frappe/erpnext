frappe.listview_settings['Project Status'] = {
	add_fields: ["indicator_color", "status"],
	get_indicator: function(doc) {
		return [__(doc.status), doc.indicator_color || frappe.utils.guess_colour(doc.status), ""];
	}
};
