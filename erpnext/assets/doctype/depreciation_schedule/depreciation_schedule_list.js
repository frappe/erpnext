frappe.listview_settings['Depreciation Schedule'] = {
	add_fields: ['status'],
	filters: [["status", "!=", "Cancelled"]],

	get_indicator: function (doc) {
		if (doc.status === "Active") {
			return [__("Active"), "green", "status,=,Active"];

		} else if (doc.status === "Cancelled") {
			return [__("Cancelled"), "grey", "status,=,Cancelled"];

		} else if (doc.status === "Draft") {
			return [__("Draft"), "red", "status,=,Draft"];
		}
	}
}
