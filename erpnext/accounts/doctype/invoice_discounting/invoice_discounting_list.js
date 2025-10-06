frappe.listview_settings["Invoice Discounting"] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (doc.status == "Draft") {
			return [__("Draft"), "red", "status,=,Draft"];
		} else if (doc.status == "Sanctioned") {
			return [__("Sanctioned"), "green", "status,=,Sanctioned"];
		} else if (doc.status == "Disbursed") {
			return [__("Disbursed"), "blue", "status,=,Disbursed"];
		} else if (doc.status == "Settled") {
			return [__("Settled"), "orange", "status,=,Settled"];
		} else if (doc.status == "Canceled") {
			return [__("Canceled"), "red", "status,=,Canceled"];
		}
	},
};
