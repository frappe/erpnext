frappe.listview_settings["Employee Advance"] = {
	get_indicator: function(doc) {
		let status_color = {
			"Draft": "red",
			"Submitted": "blue",
			"Cancelled": "red",
			"Paid": "green",
			"Unpaid": "orange",
			"Claimed": "blue",
			"Returned": "gray",
			"Partly Claimed and Returned": "yellow"
		};
		return [__(doc.status), status_color[doc.status], "status,=,"+doc.status];
	}
};