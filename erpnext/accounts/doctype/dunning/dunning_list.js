frappe.listview_settings["Dunning"] = {
	get_indicator: function (doc) {
		if (doc.status === "Resolved") {
			return [__("Resolved"), "green", "status,=,Resolved"];
		} else {
			return [__("Unresolved"), "red", "status,=,Unresolved"];
		}
	},
};
