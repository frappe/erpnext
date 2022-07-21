frappe.listview_settings['Appointment'] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (doc.status == "Open") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		} else if (doc.status == "Unconfirmed") {
			return [__(doc.status), "yellow", "status,=," + doc.status];
		} else if (doc.status == "Cancelled") {
			return [__(doc.status), "darkgrey", "status,=," + doc.status];
		} else if (doc.status == "Rescheduled") {
			return [__(doc.status), "blue", "status,=," + doc.status];
		} else if (doc.status == "Closed") {
			return [__(doc.status), "green", "status,=," + doc.status];
		}
	},
}
