frappe.listview_settings["Project"] = {
	add_fields: ["status", "priority", "percent_complete", "expected_end_date", "project_name"],
	filters: [["status", "=", "Open"]],
	get_indicator: function (doc) {
		if (doc.status == "Open" && doc.percent_complete) {
			return [__("{0}%", [cint(doc.percent_complete)]), "orange", "percent_complete,>,0|status,=,Open"];
		} else if (doc.status == "On hold") {
			return [__("On hold"), "blue", "status,=,On hold"];
		} else if (doc.status == "Disabled") {
			return [__("Disabled"), "grey", "status,=,Disabled"];
		} else {
			return [__(doc.status), frappe.utils.guess_colour(doc.status), "status,=," + doc.status];
		}
	},
};
