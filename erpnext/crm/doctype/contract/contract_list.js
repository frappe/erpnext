frappe.listview_settings["Contract"] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (doc.status == "Unsigned") {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (doc.status == "Active") {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (doc.status == "Inactive") {
			return [__(doc.status), "gray", "status,=," + doc.status];
		}
	},
};
