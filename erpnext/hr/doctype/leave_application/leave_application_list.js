frappe.listview_settings['Leave Application'] = {
	add_fields: ["status", "leave_type", "employee", "employee_name", "total_leave_days", "from_date"],
	filters:[["status","!=", "Rejected"], ["to_date", ">=", frappe.datetime.get_today()]]
};
