frappe.listview_settings["BOM Creator"] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (doc.status === "Draft") {
			return [__("Draft"), "red", "status,=,Draft"];
		} else if (doc.status === "In Progress") {
			return [__("In Progress"), "orange", "status,=,In Progress"];
		} else if (doc.status === "Completed") {
			return [__("Completed"), "green", "status,=,Completed"];
		} else if (doc.status === "Cancelled") {
			return [__("Cancelled"), "red", "status,=,Cancelled"];
		} else if (doc.status === "Failed") {
			return [__("Failed"), "red", "status,=,Failed"];
		} else if (doc.status === "Submitted") {
			return [__("Submitted"), "blue", "status,=,Submitted"];
		}
	},
};
