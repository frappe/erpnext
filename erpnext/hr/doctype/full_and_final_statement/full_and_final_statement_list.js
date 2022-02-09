frappe.listview_settings["Full and Final Statement"] = {
	get_indicator: function(doc) {
		var colors = {
			"Draft": "red",
			"Unpaid": "orange",
			"Paid": "green",
			"Cancelled": "red"
		};
		return [__(doc.status), colors[doc.status], "status,=," + doc.status];
	}
};
