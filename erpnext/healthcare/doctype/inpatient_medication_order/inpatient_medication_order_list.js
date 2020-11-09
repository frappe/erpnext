frappe.listview_settings['Inpatient Medication Order'] = {
	add_fields: ["status"],
	filters: [["status", "!=", "Cancelled"]],
	get_indicator: function(doc) {
		if (doc.status === "Pending") {
			return [__("Pending"), "orange", "status,=,Pending"];

		} else if (doc.status === "In Process") {
			return [__("In Process"), "blue", "status,=,In Process"];

		} else if (doc.status === "Completed") {
			return [__("Completed"), "green", "status,=,Completed"];

		}
	}
};
