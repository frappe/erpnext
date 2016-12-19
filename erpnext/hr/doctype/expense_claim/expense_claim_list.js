frappe.listview_settings['Expense Claim'] = {
	add_fields: ["approval_status", "total_claimed_amount", "docstatus"],
	filters:[["approval_status","!=", "Rejected"]],
	get_indicator: function(doc) {
		if(flt(doc.total_sanctioned_amount) == flt(doc.total_amount_reimbursed)) {
			return [__("Paid"), "green", "total_sanctioned_amount,=,total_amount_reimbursed"];
		} else {
			return [__("Unpaid"), "orange"];
		}
	}
};
