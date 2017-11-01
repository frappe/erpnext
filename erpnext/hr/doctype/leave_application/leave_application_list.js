frappe.listview_settings['Leave Application'] = {
	add_fields: ["status", "from_date", "to_date","leave_type", "employee", "employee_name", "total_leave_days"],
	filters:[["status","!=", "Rejected"]],
	get_indicator: function(doc) {
		return [__(doc.status),frappe.utils.guess_colour(doc.status),
			"status,=," + doc.status];
	}
	}
