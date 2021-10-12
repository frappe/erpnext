frappe.listview_settings["Employee Grievance"] = {
	has_indicator_for_draft: 1,
	get_indicator: function(doc) {
		var colors = {
			"Open": "red",
			"Investigated": "orange",
			"Resolved": "green",
			"Invalid": "grey"
		};
		return [__(doc.status), colors[doc.status], "status,=," + doc.status];
	}
};
