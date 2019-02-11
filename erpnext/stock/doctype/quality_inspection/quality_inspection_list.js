frappe.listview_settings['Quality Inspection'] = {
	add_fields: ["status", "inspection_type"],
	get_indicator: function (doc) {
		if (in_list(["Untested", "Rejected"], doc.status)) {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (in_list(["Skipped"], doc.status)) {
			return [__(doc.status), "darkgrey", "status,=," + doc.status];
		} else if (in_list(["Partially Rejected"], doc.status)) {
			return [__(doc.status), "orange", "status,=," + doc.status];
		} else if (in_list(["Accepted"], doc.status))  {
			return [__(doc.status), "green", "status,=," + doc.status];
		}
	}
};
