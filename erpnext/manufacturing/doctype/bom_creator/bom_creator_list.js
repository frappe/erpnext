frappe.listview_settings["BOM Creator"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const colors = {
			Draft: "red",
			Submitted: "blue",
			"In Progress": "orange",
			Completed: "green",
			Failed: "red",
			Superseded: "gray",
			Cancelled: "red",
		};
		return [__(doc.status), colors[doc.status], `status,=,${doc.status}`];
	},
};
