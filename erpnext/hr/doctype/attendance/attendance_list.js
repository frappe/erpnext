frappe.listview_settings['Attendance'] = {
	add_fields: ["status", "attendance_date"],
	get_indicator: function(doc) {
		if (doc.status == "Present") {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (doc.status == "Absent") {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (doc.status == "Half Day") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		} else if (doc.status == "On Leave") {
			return [__(doc.status), "blue", "status,=," + doc.status];
		} else {
			return [__(doc.status), "grey", "status,=," + doc.status];
		}
	}
};
