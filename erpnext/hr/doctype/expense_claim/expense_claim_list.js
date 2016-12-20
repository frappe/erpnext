frappe.listview_settings['Expense Claim'] = {
	add_fields: ["approval_status", "total_claimed_amount", "docstatus"],
	filters:[["approval_status","!=", "Rejected"]],
	get_indicator: function(doc) {
		if(doc.status == "Paid") {
			return [__("Paid"), "green", "status,=,'Paid'"];
		} else {
			return [__("Unpaid"), "orange"];
		}
	}
};
