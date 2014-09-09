frappe.listview_settings['Expense Claim'] = {
	add_fields: ["approval_status", "employee", "employee_name", "total_claimed_amount"],
	filters:[["approval_status","!=", "Rejected"]]
};
