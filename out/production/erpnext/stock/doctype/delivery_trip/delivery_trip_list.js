frappe.listview_settings['Delivery Trip'] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (in_list(["Cancelled", "Draft"], doc.status)) {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (in_list(["In Transit", "Scheduled"], doc.status)) {
			return [__(doc.status), "orange", "status,=," + doc.status];
		} else if (doc.status === "Completed") {
			return [__(doc.status), "green", "status,=," + doc.status];
		}
	}
};
