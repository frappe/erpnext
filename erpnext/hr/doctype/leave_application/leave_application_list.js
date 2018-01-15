frappe.listview_settings['Leave Application'] = {
	add_fields: ["workflow_state", "leave_type", "employee", "employee_name", "total_leave_days", "from_date", "to_date"],
	filters:[["workflow_state","!=", "Rejected"]],
	get_indicator: function(doc) {
		return [__(doc.workflow_state), frappe.utils.guess_colour(doc.workflow_state),
			"workflow_state,=," + doc.workflow_state];
	}
};
