frappe.listview_settings["Asset Repair"] = {
	add_fields: ["repair_status"],
	get_indicator: function (doc) {
		if (doc.repair_status == "Pending") {
			return [__("Pending"), "orange"];
		} else if (doc.repair_status == "Completed") {
			return [__("Completed"), "green"];
		} else if (doc.repair_status == "Cancelled") {
			return [__("Cancelled"), "red"];
		}
	},
};
