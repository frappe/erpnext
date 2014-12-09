frappe.listview_settings['Expense Claim'] = {
	add_fields: ["approval_status", "employee", "employee_name", 
		"total_claimed_amount", "total_amount_reimbursed", "total_sanctioned_amount", "docstatus"],
	filters:[["approval_status","!=", "Rejected"]]
};
