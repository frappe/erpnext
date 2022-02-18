frappe.listview_settings['Employee Referral'] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (doc.status == "Pending") {
			return [__(doc.status), "grey", "status,=," + doc.status];
		} else if (doc.status == "In Process") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		} else if (doc.status == "Accepted") {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (doc.status == "Rejected") {
			return [__(doc.status), "red", "status,=," + doc.status];
		}
	},
};
