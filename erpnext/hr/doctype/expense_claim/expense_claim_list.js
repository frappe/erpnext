frappe.listview_settings['Expense Claim'] = {
	add_fields: ["workflow_state", "total_claimed_amount", "docstatus"],
	filters:[["workflow_state","!=", "Rejected"]],
	get_indicator: function(doc) {
		if(doc.status == "Paid") {
			return [__("Paid"), "green", "status,=,'Paid'"];
		}else if(doc.status == "Unpaid") {
			return [__("Unpaid"), "orange"];
		} else if(doc.status == "Rejected") {
			return [__("Rejected"), "grey"];
		}
	}
};
