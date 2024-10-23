frappe.listview_settings["Delivery Trip"] = {
	add_fields: ["status"],
	has_indicator_for_draft: 1,
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
