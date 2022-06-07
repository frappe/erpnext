frappe.listview_settings["Gratuity"] = {
	get_indicator: function(doc) {
		let status_color = {
			"Draft": "red",
			"Submitted": "blue",
			"Cancelled": "red",
			"Paid": "green",
			"Unpaid": "orange",
		};
		return [__(doc.status), status_color[doc.status], "status,=,"+doc.status];
	}
};