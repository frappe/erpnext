frappe.listview_settings["Sales Forecast"] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (doc.status === "Planned") {
			// Closed
			return [__("Planned"), "orange", "status,=,Planned"];
		} else if (doc.status === "MPS Generated") {
			// on hold
			return [__("MPS Generated"), "green", "status,=,MPS Generated"];
		}
	},
};
