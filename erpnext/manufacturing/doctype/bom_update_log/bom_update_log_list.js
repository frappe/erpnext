frappe.listview_settings['BOM Update Log'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		let status_map = {
			"Queued": "orange",
			"In Progress": "blue",
			"Completed": "green",
			"Failed": "red"
		};

		return [__(doc.status), status_map[doc.status], "status,=," + doc.status];
	}
};