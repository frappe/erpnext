frappe.listview_settings['Time Log Batch'] = {
	add_fields: ["status", "total_hours"],
	get_indicator: function(doc) {
		return [__(doc.status), frappe.utils.guess_colour(doc.status), "status,=," + doc.status];
	}
};
