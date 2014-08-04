frappe.listview_settings['Time Log Batch'] = {
	add_fields: ["status", "total_hours", "rate"],
	filters:[["status","in", "Draft,Submitted"]]
};
