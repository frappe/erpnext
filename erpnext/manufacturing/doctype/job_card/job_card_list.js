frappe.listview_settings['Job Card'] = {
	has_indicator_for_draft: true,

	get_indicator: function(doc) {
		const status_colors = {
			"Work In Progress": "orange",
			"Completed": "green",
			"Cancelled": "red",
			"Material Transferred": "blue",
			"Open": "red",
		};
		const status = doc.status || "Open";
		const color = status_colors[status] || "blue";

		return [__(status), color, `status,=,${status}`];
	}
};
