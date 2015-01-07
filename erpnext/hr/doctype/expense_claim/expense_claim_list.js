frappe.listview_settings['Expense Claim'] = {
	add_fields: ["approval_status", "total_claimed_amount", "docstatus"],
	filters:[["approval_status","!=", "Rejected"]],
	get_indicator: function(doc) {
		return [__(doc.approval_status), frappe.utils.guess_colour(doc.approval_status),
			"approval_status,=," + doc.approval_status];
	}
};
