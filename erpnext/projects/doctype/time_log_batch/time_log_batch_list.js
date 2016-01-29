frappe.listview_settings['Time Log Batch'] = {
	add_fields: ["status", "total_hours"],
	get_indicator: function(doc) {
		if (doc.status== "Billed") {
			return [__("Billed"), "green", "status,=," + "Billed"]
		}
	}
};
