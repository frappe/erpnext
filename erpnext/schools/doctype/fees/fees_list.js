frappe.listview_settings['Fees'] = {
	add_fields: [ "grand_total", "paid_amount", "due_date"],
	get_indicator: function(doc) {
		var { get_today } = frappe.datetime;
		if ((doc.grand_total > doc.paid_amount) && doc.due_date < get_today()) {
			return [__("Overdue"), "red", ["due_date,<," + get_today()], ["due_date,<," + get_today()]];
		}
		else if (doc.grand_total > doc.paid_amount) {
			return [__("Pending"), "orange"];
		}
		else {
			return [__("Paid"), "green"];
		}
	}
};