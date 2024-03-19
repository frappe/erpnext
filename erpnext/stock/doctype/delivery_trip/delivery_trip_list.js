frappe.listview_settings["Delivery Trip"] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (["Cancelled", "Draft"].includes(doc.status)) {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (["In Transit", "Scheduled"].includes(doc.status)) {
			return [__(doc.status), "orange", "status,=," + doc.status];
		} else if (doc.status === "Completed") {
			return [__(doc.status), "green", "status,=," + doc.status];
		}
	},
};
