frappe.listview_settings['Project'] = {
	add_fields: ["project_status", "status", "indicator_color", "priority", "is_active", "percent_complete", "project_name"],
	get_indicator: function(doc) {
		var percentage = "";
		if (doc.percent_complete && doc.status != "Completed") {
			percentage = " " + __("({0}%)", [cint(doc.percent_complete)]);
		}

		var color_map = {
			"Open": "orange",
			"Completed": "green",
			"Closed": "green",
			"Cancelled": "darkgrey",
		}

		var guessed_color = color_map[doc.status] || frappe.utils.guess_colour(doc.status);

		if (doc.project_status) {
			return [
				__(doc.project_status) + percentage,
				doc.indicator_color || guessed_color,
				"project_status,=," + doc.project_status
			];
		} else {
			return [
				__(doc.status) + percentage,
				guessed_color,
				"status,=," + doc.status
			];
		}
	},
};
