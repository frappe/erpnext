frappe.listview_settings['Customer Feedback'] = {
	get_indicator: function(doc) {
		if(doc.status == "Pending") {
			var color = "orange";
		} else if (doc.status == "Completed") {
			var color = "green";
		}
		return [__(doc.status), color, "status,=," + doc.status]
	},
};
