frappe.listview_settings['Project'] = {
	add_fields: ["status", "priority", "is_active", "percent_complete",
		"percent_milestones_completed", "completion_date"],
	filters:[["status","=", "Open"]]
};
