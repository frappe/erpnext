frappe.listview_settings['Project'] = {
	add_fields: ["status", "priority", "is_active", "percent_complete", "expected_end_date", "project_name"],
	get_indicator: function(doc) {
		var percentage = "";
		if (doc.percent_complete) {
			percentage = " " + __("({0}%)", [cint(doc.percent_complete)]);
		}

		if(doc.status == "Open") {
			return [__(doc.status) + percentage, "orange", "status,=," + doc.status];
		} else if (doc.status == "To Bill") {
			return [__(doc.status) + percentage, "purple", "status,=," + doc.status];
		} else if (doc.status == "Completed") {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (doc.status == "Cancelled") {
			return [__(doc.status), "darkgrey", "status,=," + doc.status];
		} else {
			return [__(doc.status), frappe.utils.guess_colour(doc.status), "status,=," + doc.status];
		}
	}
};
