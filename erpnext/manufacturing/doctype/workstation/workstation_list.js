frappe.listview_settings["Workstation"] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		let color_map = {
			Production: "green",
			Off: "gray",
			Idle: "gray",
			Problem: "red",
			Maintenance: "yellow",
			Setup: "blue",
		};

		return [__(doc.status), color_map[doc.status], true];
	},
};
