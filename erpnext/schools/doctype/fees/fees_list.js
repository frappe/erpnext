frappe.listview_settings['Fees'] = {
	add_fields: [ "total_amount", "paid_amount", "due_date"],
	get_indicator: function(doc) {
		if ((doc.total_amount > doc.paid_amount) && doc.due_date < get_today()) {
			return [__("Overdue"), "red", ["due_date,<,"+get_today()], ["due_date,<,"+get_today()]];
		}
		else if (doc.total_amount > doc.paid_amount) {
			return [__("Pending"), "orange"];
		}
		else {
			return [__("Paid"), "green"];
		}
	}
};