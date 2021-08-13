frappe.listview_settings['Overtime Slip'] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (doc.status == "Approved") {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (doc.status == "Rejected") {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (doc.status == "Pending") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		}
	},
};